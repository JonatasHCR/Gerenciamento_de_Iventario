from datetime import datetime
from http import HTTPStatus
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.model.associacao_user_contrato import AssociacaoUserContrato
from backend.model.cessao import (
    Cessao,
    CessaoEletronico,
    CessaoPeriferico,
)
from backend.model.contratos import Contrato
from backend.model.eletronicos import Eletronico
from backend.model.solicitacao import (
    Solicitacao,
    SolicitacaoEletronico,
    SolicitacaoPeriferico,
)
from backend.model.user import User
from backend.schemas.solicitacoes import (
    SolicitacaoCargoInicialCreate,
    SolicitacaoCessaoCreate,
    SolicitacaoConviteCCCreate,
    SolicitacaoEntradaCCCreate,
)
from backend.security.dependencies import UserContext
from backend.service.audit_log import log as audit_log


class SolicitacaoService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _get_by_id(self, solicitacao_id: int) -> Solicitacao:
        result = await self.session.execute(
            select(Solicitacao).where(Solicitacao.id == solicitacao_id)
        )
        sol = result.scalar_one_or_none()
        if sol is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail='Solicitação não encontrada.',
            )
        return sol

    async def _assert_cc_exists(self, centro_custo: str) -> None:
        result = await self.session.execute(
            select(Contrato).where(
                Contrato.centro_custo == centro_custo
            )
        )
        if result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail='Centro de custo não encontrado.',
            )

    async def _assert_not_in_cc(
        self, user_id: int, centro_custo: str
    ) -> None:
        result = await self.session.execute(
            select(AssociacaoUserContrato).where(
                AssociacaoUserContrato.user_id == user_id,
                AssociacaoUserContrato.centro_custo == centro_custo,
            )
        )
        if result.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail='Usuário já está associado a este centro de custo.',
            )

    async def _assert_no_pending_cc(
        self, user_id: int, centro_custo: str
    ) -> None:
        result = await self.session.execute(
            select(Solicitacao).where(
                Solicitacao.solicitante_id == user_id,
                Solicitacao.centro_custo == centro_custo,
                Solicitacao.tipo == 'entrada_cc',
                Solicitacao.status == 'pendente',
            )
        )
        if result.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail='Já existe uma solicitação pendente para este CC.',
            )

    async def _eletronicos_da_solicitacao(
        self, solicitacao_id: int
    ) -> list[Eletronico]:
        result = await self.session.execute(
            select(Eletronico)
            .join(
                SolicitacaoEletronico,
                SolicitacaoEletronico.eletronico_id == Eletronico.id,
            )
            .where(SolicitacaoEletronico.solicitacao_id == solicitacao_id)
        )
        return list(result.scalars().all())

    async def _perifericos_da_solicitacao(
        self, solicitacao_id: int
    ) -> list[SolicitacaoPeriferico]:
        result = await self.session.execute(
            select(SolicitacaoPeriferico)
            .where(SolicitacaoPeriferico.solicitacao_id == solicitacao_id)
            .order_by(SolicitacaoPeriferico.id)
        )
        return list(result.scalars().all())

    @staticmethod
    def _periferico_to_dict(p: SolicitacaoPeriferico) -> dict:
        return {'nome': p.nome, 'quantidade': p.quantidade}

    @staticmethod
    def _eletronico_to_dict(el: Eletronico) -> dict:
        return {
            'id': el.id,
            'numero_serie': el.numero_serie,
            'numero_patrimonio': el.numero_patrimonio,
            'nome': el.nome,
            'marca': el.marca,
            'tipo': el.tipo,
            'modelo': el.modelo,
            'status': el.status,
            'ip': el.ip,
            'localizacao': el.localizacao,
            'descricao': el.descricao,
            'centro_custo': el.centro_custo,
        }

    async def _serialize(self, sol: Solicitacao) -> dict:
        data = {
            'id': sol.id,
            'tipo': sol.tipo,
            'status': sol.status,
            'solicitante_id': sol.solicitante_id,
            'centro_custo': sol.centro_custo,
            'ocupacao_solicitada': sol.ocupacao_solicitada,
            'convidado_por_id': sol.convidado_por_id,
            'cargo_solicitado': sol.cargo_solicitado,
            'centro_custo_destino': sol.centro_custo_destino,
            'responsavel': sol.responsavel,
            'criado_em': sol.criado_em,
            'eletronicos': [],
            'perifericos': [],
        }
        if sol.tipo == 'cessao':
            els = await self._eletronicos_da_solicitacao(sol.id)
            data['eletronicos'] = [
                self._eletronico_to_dict(e) for e in els
            ]
            perifs = await self._perifericos_da_solicitacao(sol.id)
            data['perifericos'] = [
                self._periferico_to_dict(p) for p in perifs
            ]
        return data

    async def _batch_eletronicos(
        self, sol_ids: list[int]
    ) -> dict[int, list[Eletronico]]:
        if not sol_ids:
            return {}
        result = await self.session.execute(
            select(
                Eletronico,
                SolicitacaoEletronico.solicitacao_id,
            )
            .join(
                SolicitacaoEletronico,
                SolicitacaoEletronico.eletronico_id == Eletronico.id,
            )
            .where(
                SolicitacaoEletronico.solicitacao_id.in_(sol_ids)
            )
        )
        batch: dict[int, list[Eletronico]] = {}
        for el, sol_id in result.all():
            batch.setdefault(sol_id, []).append(el)
        return batch

    async def _batch_perifericos(
        self, sol_ids: list[int]
    ) -> dict[int, list[SolicitacaoPeriferico]]:
        if not sol_ids:
            return {}
        result = await self.session.execute(
            select(SolicitacaoPeriferico)
            .where(SolicitacaoPeriferico.solicitacao_id.in_(sol_ids))
            .order_by(SolicitacaoPeriferico.id)
        )
        batch: dict[int, list[SolicitacaoPeriferico]] = {}
        for p in result.scalars().all():
            batch.setdefault(p.solicitacao_id, []).append(p)
        return batch

    async def _serializar_lista(
        self, sols: list[Solicitacao]
    ) -> list[dict]:
        cessao_ids = [s.id for s in sols if s.tipo == 'cessao']
        batch = await self._batch_eletronicos(cessao_ids)
        batch_perifs = await self._batch_perifericos(cessao_ids)
        out = []
        for sol in sols:
            data = {
                'id': sol.id,
                'tipo': sol.tipo,
                'status': sol.status,
                'solicitante_id': sol.solicitante_id,
                'centro_custo': sol.centro_custo,
                'ocupacao_solicitada': sol.ocupacao_solicitada,
                'convidado_por_id': sol.convidado_por_id,
                'cargo_solicitado': sol.cargo_solicitado,
                'centro_custo_destino': sol.centro_custo_destino,
                'responsavel': sol.responsavel,
                'criado_em': sol.criado_em,
                'eletronicos': [],
                'perifericos': [],
            }
            if sol.tipo == 'cessao':
                data['eletronicos'] = [
                    self._eletronico_to_dict(e)
                    for e in batch.get(sol.id, [])
                ]
                data['perifericos'] = [
                    self._periferico_to_dict(p)
                    for p in batch_perifs.get(sol.id, [])
                ]
            out.append(data)
        return out

    async def get(self, ctx: UserContext):
        if ctx.is_privileged:
            result = await self.session.execute(select(Solicitacao))
            sols = list(result.scalars().all())
            return await self._serializar_lista(sols)

        gestor_ccs = [
            cc for cc, ocup in ctx.ocupacoes.items() if ocup == 'Gestor'
        ]
        subgestor_ccs = [
            cc
            for cc, ocup in ctx.ocupacoes.items()
            if ocup == 'Subgestor'
        ]

        conditions = [Solicitacao.solicitante_id == ctx.user.id]

        if gestor_ccs:
            conditions.append(
                and_(
                    Solicitacao.tipo == 'entrada_cc',
                    Solicitacao.status == 'pendente',
                    Solicitacao.convidado_por_id.is_(None),
                    Solicitacao.centro_custo.in_(gestor_ccs),
                )
            )
            # Gestor vê pedidos de cessão do seu CC (origem dos itens)
            conditions.append(
                and_(
                    Solicitacao.tipo == 'cessao',
                    Solicitacao.status == 'pendente',
                    Solicitacao.centro_custo.in_(gestor_ccs),
                )
            )

        if subgestor_ccs:
            conditions.append(
                and_(
                    Solicitacao.tipo == 'entrada_cc',
                    Solicitacao.status == 'pendente',
                    Solicitacao.convidado_por_id.is_(None),
                    Solicitacao.centro_custo.in_(subgestor_ccs),
                    Solicitacao.ocupacao_solicitada == 'Funcionario',
                )
            )

        result = await self.session.execute(
            select(Solicitacao).where(or_(*conditions))
        )
        sols = list(result.scalars().all())
        return await self._serializar_lista(sols)

    async def create_entrada_cc(
        self,
        data: SolicitacaoEntradaCCCreate,
        ctx: UserContext,
    ):
        await self._assert_cc_exists(data.centro_custo)
        await self._assert_not_in_cc(ctx.user.id, data.centro_custo)
        await self._assert_no_pending_cc(ctx.user.id, data.centro_custo)

        nova = Solicitacao(
            tipo='entrada_cc',
            status='pendente',
            solicitante_id=ctx.user.id,
            centro_custo=data.centro_custo,
            ocupacao_solicitada=data.ocupacao_solicitada,
        )
        self.session.add(nova)
        await self.session.commit()
        await self.session.refresh(nova)
        return await self._serialize(nova)

    async def create_convite_cc(
        self,
        data: SolicitacaoConviteCCCreate,
        ctx: UserContext,
    ):
        if not ctx.is_privileged:
            ocupacao_no_cc = ctx.ocupacoes.get(data.centro_custo)
            if ocupacao_no_cc not in {'Gestor', 'Subgestor'}:
                raise HTTPException(
                    status_code=HTTPStatus.FORBIDDEN,
                    detail=(
                        'Apenas Gestor, Subgestor do CC ou Admin '
                        'pode convidar.'
                    ),
                )
            if (
                ocupacao_no_cc == 'Subgestor'
                and data.ocupacao_solicitada != 'Funcionario'
            ):
                raise HTTPException(
                    status_code=HTTPStatus.FORBIDDEN,
                    detail=(
                        'Subgestor só pode convidar para Funcionario.'
                    ),
                )

        result = await self.session.execute(
            select(User).where(User.id == data.solicitante_id)
        )
        if result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail='Usuário convidado não encontrado.',
            )

        await self._assert_cc_exists(data.centro_custo)
        await self._assert_not_in_cc(
            data.solicitante_id, data.centro_custo
        )
        await self._assert_no_pending_cc(
            data.solicitante_id, data.centro_custo
        )

        nova = Solicitacao(
            tipo='entrada_cc',
            status='pendente',
            solicitante_id=data.solicitante_id,
            centro_custo=data.centro_custo,
            ocupacao_solicitada=data.ocupacao_solicitada,
            convidado_por_id=ctx.user.id,
        )
        self.session.add(nova)
        await self.session.commit()
        await self.session.refresh(nova)
        return await self._serialize(nova)

    async def create_cargo_inicial(
        self,
        data: SolicitacaoCargoInicialCreate,
        ctx: UserContext,
    ):
        result = await self.session.execute(
            select(Solicitacao).where(
                Solicitacao.solicitante_id == ctx.user.id,
                Solicitacao.tipo == 'cargo_inicial',
                Solicitacao.status == 'pendente',
            )
        )
        if result.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail='Já existe uma solicitação de cargo pendente.',
            )

        nova = Solicitacao(
            tipo='cargo_inicial',
            status='pendente',
            solicitante_id=ctx.user.id,
            cargo_solicitado=data.cargo_solicitado,
        )
        self.session.add(nova)
        await self.session.commit()
        await self.session.refresh(nova)
        return await self._serialize(nova)

    async def create_cessao(
        self,
        data: SolicitacaoCessaoCreate,
        ctx: UserContext,
    ):
        """
        Subgestor solicita cessão ao Gestor do CC. Equipamentos devem:
        - Pertencer a um único CC (CC de origem).
        - O solicitante deve ser Subgestor desse CC.
        - Estar `Interno`.
        """
        if ctx.is_privileged or ctx.is_tecnico_ti:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail=(
                    'Admin/Tecnico_TI cedem direto via /cessoes, '
                    'sem solicitação.'
                ),
            )

        # Carrega eletrônicos
        result = await self.session.execute(
            select(Eletronico).where(
                Eletronico.id.in_(data.eletronico_ids)
            )
        )
        eletronicos = list(result.scalars().all())
        encontrados = {e.id for e in eletronicos}
        faltando = set(data.eletronico_ids) - encontrados
        if faltando:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=f'Eletrônicos não encontrados: {sorted(faltando)}',
            )

        # Mesmo CC de origem
        ccs_origem = {e.centro_custo for e in eletronicos}
        if len(ccs_origem) != 1:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail=(
                    'Todos os equipamentos devem ser do mesmo CC '
                    'de origem.'
                ),
            )
        cc_origem = next(iter(ccs_origem))

        # Usuário é Subgestor desse CC?
        if ctx.ocupacoes.get(cc_origem) != 'Subgestor':
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail=(
                    'Apenas Subgestor do CC de origem pode solicitar.'
                ),
            )

        await self._assert_cc_exists(data.centro_custo_destino)

        for e in eletronicos:
            if e.status != 'Interno':
                raise HTTPException(
                    status_code=HTTPStatus.CONFLICT,
                    detail=(
                        f'Eletrônico {e.id} ({e.nome}) não está Interno '
                        f'(status: {e.status}).'
                    ),
                )

        nova = Solicitacao(
            tipo='cessao',
            status='pendente',
            solicitante_id=ctx.user.id,
            centro_custo=cc_origem,
            centro_custo_destino=data.centro_custo_destino,
            responsavel=data.responsavel,
        )
        self.session.add(nova)
        await self.session.flush()

        for e in eletronicos:
            self.session.add(
                SolicitacaoEletronico(
                    solicitacao_id=nova.id,
                    eletronico_id=e.id,
                )
            )

        for p in data.perifericos:
            self.session.add(
                SolicitacaoPeriferico(
                    solicitacao_id=nova.id,
                    nome=p.nome.strip(),
                    quantidade=p.quantidade,
                )
            )

        await self.session.commit()
        await self.session.refresh(nova)
        return await self._serialize(nova)

    @staticmethod
    async def _assert_can_decide(
        sol: Solicitacao, ctx: UserContext
    ) -> None:
        if sol.tipo == 'cargo_inicial':
            if not ctx.is_privileged:
                raise HTTPException(
                    status_code=HTTPStatus.FORBIDDEN,
                    detail='Apenas Admin pode decidir solicitações de cargo.',
                )
            return

        if sol.tipo == 'cessao':
            if ctx.is_privileged:
                return
            if ctx.ocupacoes.get(sol.centro_custo) == 'Gestor':
                return
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail=(
                    'Apenas Gestor do CC de origem ou Admin pode '
                    'decidir esta solicitação.'
                ),
            )

        # entrada_cc — pedido do usuário (sem convite)
        if sol.convidado_por_id is None:
            if ctx.is_privileged:
                return
            ocupacao_no_cc = ctx.ocupacoes.get(sol.centro_custo)
            if ocupacao_no_cc == 'Gestor':
                return
            if ocupacao_no_cc == 'Subgestor':
                if sol.ocupacao_solicitada != 'Funcionario':
                    raise HTTPException(
                        status_code=HTTPStatus.FORBIDDEN,
                        detail=(
                            'Subgestor só pode aprovar/rejeitar '
                            'solicitações de cargo Funcionario.'
                        ),
                    )
                return
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail=(
                    'Apenas Gestor/Subgestor do CC ou Admin pode decidir.'
                ),
            )

        # entrada_cc — convite do Gestor; o convidado aceita/rejeita
        if not ctx.is_privileged and ctx.user.id != sol.solicitante_id:
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail=(
                    'Apenas o usuário convidado ou Admin pode '
                    'aceitar/rejeitar este convite.'
                ),
            )

    async def _criar_cessao_da_solicitacao(
        self, sol: Solicitacao, ctx: UserContext
    ) -> None:
        """Cria uma Cessao a partir de uma Solicitacao aprovada."""
        eletronicos = await self._eletronicos_da_solicitacao(sol.id)
        if not eletronicos:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail='Solicitação sem equipamentos.',
            )

        for e in eletronicos:
            if e.status != 'Interno':
                raise HTTPException(
                    status_code=HTTPStatus.CONFLICT,
                    detail=(
                        f'Eletrônico {e.id} ({e.nome}) não está '
                        f'mais Interno; não é possível ceder.'
                    ),
                )

        cessao = Cessao(
            responsavel=sol.responsavel,
            centro_custo_destino=sol.centro_custo_destino,
            cedido_por_id=ctx.user.id,
            cedido_em=datetime.now(tz=ZoneInfo('America/Sao_Paulo')),
        )
        self.session.add(cessao)
        await self.session.flush()

        for e in eletronicos:
            e.status = 'Externo'
            e.localizacao = f'Cedido para CC {sol.centro_custo_destino}'
            self.session.add(
                CessaoEletronico(
                    cessao_id=cessao.id,
                    eletronico_id=e.id,
                )
            )

        # Copia os periféricos propostos na solicitação para a cessão real
        perifs = await self._perifericos_da_solicitacao(sol.id)
        for p in perifs:
            self.session.add(
                CessaoPeriferico(
                    cessao_id=cessao.id,
                    nome=p.nome,
                    quantidade=p.quantidade,
                )
            )

    async def _aprovar_entrada_cc(self, sol: Solicitacao) -> None:
        assoc = AssociacaoUserContrato(
            user_id=sol.solicitante_id,
            centro_custo=sol.centro_custo,
            ocupacao=sol.ocupacao_solicitada,
        )
        try:
            self.session.add(assoc)
            await self.session.flush()
        except IntegrityError:
            await self.session.rollback()
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail='Usuário já está associado a este CC.',
            )

    async def _aprovar_cargo_inicial(self, sol: Solicitacao) -> None:
        result = await self.session.execute(
            select(User).where(User.id == sol.solicitante_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail='Usuário não encontrado.',
            )
        user.tipo = sol.cargo_solicitado

    async def aprovar(self, solicitacao_id: int, ctx: UserContext):
        sol = await self._get_by_id(solicitacao_id)

        if sol.status != 'pendente':
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail='Apenas solicitações pendentes podem ser aprovadas.',
            )

        await self._assert_can_decide(sol, ctx)

        if sol.tipo == 'entrada_cc':
            await self._aprovar_entrada_cc(sol)
        elif sol.tipo == 'cessao':
            await self._criar_cessao_da_solicitacao(sol, ctx)
        else:
            await self._aprovar_cargo_inicial(sol)

        sol.status = 'aprovada'
        audit_log(
            self.session,
            action='solicitacao.aprovar',
            user_id=ctx.user.id,
            target_type='solicitacao',
            target_id=sol.id,
            payload={
                'tipo': sol.tipo,
                'solicitante_id': sol.solicitante_id,
                'centro_custo': sol.centro_custo,
                'ocupacao_solicitada': sol.ocupacao_solicitada,
                'cargo_solicitado': sol.cargo_solicitado,
                'centro_custo_destino': sol.centro_custo_destino,
            },
        )
        await self.session.commit()
        await self.session.refresh(sol)
        return await self._serialize(sol)

    async def rejeitar(self, solicitacao_id: int, ctx: UserContext):
        sol = await self._get_by_id(solicitacao_id)

        if sol.status != 'pendente':
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail='Apenas solicitações pendentes podem ser rejeitadas.',
            )

        await self._assert_can_decide(sol, ctx)
        sol.status = 'rejeitada'
        audit_log(
            self.session,
            action='solicitacao.rejeitar',
            user_id=ctx.user.id,
            target_type='solicitacao',
            target_id=sol.id,
            payload={'tipo': sol.tipo, 'solicitante_id': sol.solicitante_id},
        )
        await self.session.commit()
        await self.session.refresh(sol)
        return await self._serialize(sol)

    async def cancelar(self, solicitacao_id: int, ctx: UserContext):
        sol = await self._get_by_id(solicitacao_id)

        if ctx.is_privileged:
            # Admin apaga qualquer solicitação, em qualquer status.
            snapshot = await self._serialize(sol)
            audit_log(
                self.session,
                action='solicitacao.delete',
                user_id=ctx.user.id,
                target_type='solicitacao',
                target_id=sol.id,
                payload={
                    'tipo': sol.tipo,
                    'status': sol.status,
                    'solicitante_id': sol.solicitante_id,
                },
            )
            await self.session.delete(sol)
            await self.session.commit()
            return snapshot

        if sol.status != 'pendente':
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail='Apenas solicitações pendentes podem ser canceladas.',
            )

        if ctx.user.id != sol.solicitante_id:
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail=(
                    'Apenas o solicitante ou Admin pode cancelar.'
                ),
            )

        snapshot = await self._serialize(sol)
        audit_log(
            self.session,
            action='solicitacao.cancelar',
            user_id=ctx.user.id,
            target_type='solicitacao',
            target_id=sol.id,
            payload={'tipo': sol.tipo},
        )
        await self.session.delete(sol)
        await self.session.commit()
        return snapshot
