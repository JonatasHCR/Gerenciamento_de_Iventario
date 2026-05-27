from http import HTTPStatus

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.model.associacao_user_contrato import AssociacaoUserContrato
from backend.model.contratos import Contrato
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
        """Apenas Admin ou Gestor do próprio CC (por ocupação)."""
        ctx.assert_cc_role(centro_custo, 'Gestor')

        result = await self.session.execute(
            select(Contrato).where(Contrato.centro_custo == centro_custo)
        )
        existing = result.scalar_one_or_none()
        if existing is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail='Contrato não encontrado.',
            )

        data = contrato.model_dump(exclude_unset=True)
        antes = {'descricao': existing.descricao}
        for key, value in data.items():
            setattr(existing, key, value)

        audit_log(
            self.session,
            action='contrato.update',
            user_id=ctx.user.id,
            target_type='contrato',
            target_id=None,
            payload={
                'centro_custo': centro_custo,
                'antes': antes,
                'depois': data,
            },
        )

        await self.session.commit()
        await self.session.refresh(existing)
        return existing

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
