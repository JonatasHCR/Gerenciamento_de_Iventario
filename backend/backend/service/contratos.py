from http import HTTPStatus

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy import update as sa_update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.model.associacao_user_contrato import AssociacaoUserContrato
from backend.model.cessao import Cessao
from backend.model.contratos import Contrato
from backend.model.eletronicos import Eletronico
from backend.model.solicitacao import Solicitacao
from backend.model.user import User
from backend.schemas.contratos import ContratoCreate
from backend.security.dependencies import UserContext
from backend.service.associacoes import AssociacaoUserContratoService
from backend.service.audit_log import log as audit_log


class ContratoService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, ctx: UserContext):  # noqa: ARG002
        """
        Todos os usuários autenticados veem todos os CCs (com nome do
        Gestor + total de membros) para poder solicitar entrada.
        As permissões de write continuam restritas em
        create/update/delete. `ctx` é mantido na assinatura por
        consistência com os demais services e para reforçar a
        obrigatoriedade da autenticação no nível do router.
        """
        contratos = (
            await self.session.execute(select(Contrato))
        ).scalars().all()

        # Total de membros por CC
        totais_q = await self.session.execute(
            select(
                AssociacaoUserContrato.centro_custo,
                func.count(AssociacaoUserContrato.user_id),
            ).group_by(AssociacaoUserContrato.centro_custo)
        )
        totais = {cc: n for cc, n in totais_q.all()}

        # Nome do Gestor de cada CC (pega o primeiro caso haja >1)
        gestores_q = await self.session.execute(
            select(AssociacaoUserContrato.centro_custo, User.nome)
            .join(User, User.id == AssociacaoUserContrato.user_id)
            .where(AssociacaoUserContrato.ocupacao == 'Gestor')
        )
        gestores: dict[str, str] = {}
        for cc, nome in gestores_q.all():
            gestores.setdefault(cc, nome)

        return [
            {
                'centro_custo': c.centro_custo,
                'descricao': c.descricao,
                'gestor_nome': gestores.get(c.centro_custo),
                'total_membros': totais.get(c.centro_custo, 0),
            }
            for c in contratos
        ]

    async def create(self, contrato: ContratoCreate, ctx: UserContext):
        """Apenas Admin ou Gestor"""
        ctx.assert_write('Gestor')
        try:
            novo = Contrato(**contrato.model_dump())
            self.session.add(novo)
            await self.session.flush()
            audit_log(
                self.session,
                action='contrato.create',
                user_id=ctx.user.id,
                target_type='contrato',
                target_id=None,
                payload={
                    'centro_custo': novo.centro_custo,
                    'descricao': novo.descricao,
                },
            )
            # Associa o criador como Gestor na mesma transação
            assoc_service = AssociacaoUserContratoService(self.session)
            await assoc_service.add_gestor_inicial(
                ctx.user.id, novo.centro_custo, ctx
            )
            await self.session.commit()
            await self.session.refresh(novo)
        except IntegrityError:
            await self.session.rollback()
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail='numero de centro de custo já existe',
            )
        return novo

    async def update(
        self, centro_custo: str, contrato: ContratoCreate, ctx: UserContext
    ):
        """
        Apenas Admin ou Gestor do próprio CC (por ocupação).

        Permite **renomear o código do CC** (a PK). Quando o código muda,
        a alteração é propagada para tudo que referencia o CC:
        equipamentos, associações, solicitações (FK com ON UPDATE CASCADE)
        e as colunas-string sem FK (destino de cessões/solicitações).

        No Postgres os FKs com ON UPDATE CASCADE propagam sozinhos; os
        UPDATEs explícitos abaixo cobrem as colunas sem FK e o ambiente
        de teste (SQLite com FK desligado).
        """
        ctx.assert_cc_role(centro_custo, 'Gestor')

        atual = await self.session.scalar(
            select(Contrato.centro_custo).where(
                Contrato.centro_custo == centro_custo
            )
        )
        if atual is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail='Contrato não encontrado.',
            )

        novo_cc = contrato.centro_custo
        renomeando = novo_cc != centro_custo

        if renomeando:
            colide = await self.session.scalar(
                select(Contrato.centro_custo).where(
                    Contrato.centro_custo == novo_cc
                )
            )
            if colide is not None:
                raise HTTPException(
                    status_code=HTTPStatus.CONFLICT,
                    detail='Já existe um centro de custo com esse código.',
                )

        try:
            await self.session.execute(
                sa_update(Contrato)
                .where(Contrato.centro_custo == centro_custo)
                .values(centro_custo=novo_cc, descricao=contrato.descricao)
            )

            if renomeando:
                propagacoes = (
                    sa_update(Eletronico)
                    .where(Eletronico.centro_custo == centro_custo)
                    .values(centro_custo=novo_cc),
                    sa_update(AssociacaoUserContrato)
                    .where(AssociacaoUserContrato.centro_custo == centro_custo)
                    .values(centro_custo=novo_cc),
                    sa_update(Solicitacao)
                    .where(Solicitacao.centro_custo == centro_custo)
                    .values(centro_custo=novo_cc),
                    sa_update(Cessao)
                    .where(Cessao.centro_custo_destino == centro_custo)
                    .values(centro_custo_destino=novo_cc),
                    sa_update(Solicitacao)
                    .where(Solicitacao.centro_custo_destino == centro_custo)
                    .values(centro_custo_destino=novo_cc),
                )
                for stmt in propagacoes:
                    await self.session.execute(
                        stmt.execution_options(synchronize_session=False)
                    )

            audit_log(
                self.session,
                action='contrato.update',
                user_id=ctx.user.id,
                target_type='contrato',
                target_id=None,
                payload={
                    'centro_custo': centro_custo,
                    'antes': {'centro_custo': centro_custo},
                    'depois': {
                        'centro_custo': novo_cc,
                        'descricao': contrato.descricao,
                    },
                },
            )

            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail='numero de centro de custo já existe',
            )

        result = await self.session.execute(
            select(Contrato).where(Contrato.centro_custo == novo_cc)
        )
        return result.scalar_one()

    async def delete(self, centro_custo: str, ctx: UserContext):
        """Apenas Admin ou Gestor do próprio CC (por ocupação)."""
        ctx.assert_cc_role(centro_custo, 'Gestor')

        result = await self.session.execute(
            select(Contrato).where(Contrato.centro_custo == centro_custo)
        )
        contrato = result.scalar_one_or_none()
        if contrato is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail='Contrato não encontrado.',
            )
        audit_log(
            self.session,
            action='contrato.delete',
            user_id=ctx.user.id,
            target_type='contrato',
            target_id=None,
            payload={
                'centro_custo': contrato.centro_custo,
                'descricao': contrato.descricao,
            },
        )
        await self.session.delete(contrato)
        await self.session.commit()
        return contrato
