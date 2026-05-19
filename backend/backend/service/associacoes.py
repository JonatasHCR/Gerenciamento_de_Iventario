from http import HTTPStatus

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.model.associacao_user_contrato import AssociacaoUserContrato
from backend.model.associacao_user_eletronico import AssociacaoUserEletronico
from backend.model.eletronicos import Eletronico
from backend.schemas.associacoes import (
    AssociacaoUserContratoCreate,
    AssociacaoUserEletronicoCreate,
)
from backend.security.dependencies import UserContext

# ─── AssociacaoUserContratoService


class AssociacaoUserContratoService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, ctx: UserContext):
        """
        - Admin/TI → todas.
        - Demais → apenas do(s) seu(s) CC(s).
        """
        if ctx.is_privileged or ctx.is_tecnico_ti:
            result = await self.session.execute(select(AssociacaoUserContrato))
            return result.scalars().all()

        if not ctx.centros_custo:
            return []

        result = await self.session.execute(
            select(AssociacaoUserContrato).where(
                AssociacaoUserContrato.centro_custo.in_(ctx.centros_custo)
            )
        )
        return result.scalars().all()

    async def get_by_ids(
        self, user_id: int, centro_custo: str
    ) -> AssociacaoUserContrato:
        result = await self.session.execute(
            select(AssociacaoUserContrato).where(
                AssociacaoUserContrato.user_id == user_id,
                AssociacaoUserContrato.centro_custo == centro_custo,
            )
        )
        assoc = result.scalar_one_or_none()
        if assoc is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail='Associação usuário-contrato não encontrada.',
            )
        return assoc

    async def create(
        self, data: AssociacaoUserContratoCreate, ctx: UserContext
    ):
        """
        Autorização per-CC (ocupação no CC alvo):
        - Admin → qualquer.
        - Gestor do CC → qualquer ocupação.
        - Subgestor do CC → apenas ocupação 'Funcionario'.
        - Demais → 403.

        Se o CC ainda não tem associações (CC recém-criado pelo
        método create do ContratoService) a primeira associação é
        permitida sem assert (essa lógica é interna e segura).
        """
        result = await self.session.execute(
            select(AssociacaoUserContrato).where(
                AssociacaoUserContrato.centro_custo == data.centro_custo
            )
        )
        cc_ja_tem_membros = result.scalar_one_or_none() is not None

        if cc_ja_tem_membros:
            ctx.assert_cc_role(
                data.centro_custo, 'Gestor', 'Subgestor'
            )
            if (
                not ctx.is_privileged
                and ctx.ocupacao_in(data.centro_custo) == 'Subgestor'
                and data.ocupacao != 'Funcionario'
            ):
                raise HTTPException(
                    status_code=HTTPStatus.FORBIDDEN,
                    detail='Subgestor só pode adicionar Funcionários.',
                )

        nova = AssociacaoUserContrato(**data.model_dump())
        try:
            self.session.add(nova)
            await self.session.commit()
            await self.session.refresh(nova)
            return nova
        except IntegrityError:
            await self.session.rollback()
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail='Associação já existe ou usuário/contrato inválido.',
            )

    async def update(
        self,
        user_id: int,
        centro_custo: str,
        data: AssociacaoUserContratoCreate,
        ctx: UserContext,
    ):
        """
        - Admin → qualquer.
        - Gestor do CC → permitido.
        - Demais → 403.
        """
        ctx.assert_cc_role(centro_custo, 'Gestor')

        assoc = await self.get_by_ids(user_id, centro_custo)
        try:
            for key, value in data.model_dump(exclude_unset=True).items():
                setattr(assoc, key, value)
            await self.session.commit()
            await self.session.refresh(assoc)
            return assoc
        except IntegrityError:
            await self.session.rollback()
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail='Associação já existe ou usuário/contrato inválido.',
            )

    async def delete(self, user_id: int, centro_custo: str, ctx: UserContext):
        """
        - Admin/TI → qualquer.
        - Self-removal → qualquer usuário pode sair do CC,
          exceto se for o único Gestor.
        - Gestor → qualquer usuário do seu CC.
        - Subgestor → apenas Funcionários do seu CC.
        - Funcionario → 403 (exceto self).
        """
        is_self = ctx.user.id == user_id

        if not is_self:
            ctx.assert_cc_role(centro_custo, 'Gestor', 'Subgestor')

        assoc = await self.get_by_ids(user_id, centro_custo)

        if (
            not is_self
            and not ctx.is_privileged
            and ctx.ocupacao_in(centro_custo) == 'Subgestor'
            and assoc.ocupacao != 'Funcionario'
        ):
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail='Subgestor só pode remover Funcionários.',
            )

        if assoc.ocupacao == 'Gestor':
            outros = await self.session.execute(
                select(AssociacaoUserContrato).where(
                    AssociacaoUserContrato.centro_custo == centro_custo,
                    AssociacaoUserContrato.ocupacao == 'Gestor',
                    AssociacaoUserContrato.user_id != user_id,
                )
            )
            if outros.scalar_one_or_none() is None:
                raise HTTPException(
                    status_code=HTTPStatus.CONFLICT,
                    detail=(
                        'Este é o único Gestor deste CC. '
                        'Nomeie outro Gestor antes de remover.'
                    ),
                )

        await self.session.delete(assoc)
        await self.session.commit()
        return assoc


# ─── AssociacaoUserEletronicoService


class AssociacaoUserEletronicoService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _get_eletronico_cc(self, eletronico_id: int) -> str:
        """Retorna o centro_custo do eletrônico ou lança 404."""
        result = await self.session.execute(
            select(Eletronico).where(Eletronico.id == eletronico_id)
        )
        eletronico = result.scalar_one_or_none()
        if eletronico is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail='Eletrônico não encontrado.',
            )
        return eletronico.centro_custo

    async def get(self, ctx: UserContext):
        """
        Visibilidade por ocupação per-CC:
        - Admin/Tecnico_TI → todas.
        - Em CCs onde é Gestor/Subgestor → todas as associações
          daqueles CCs.
        - Em CCs onde é Funcionario → apenas as próprias associações
          (em qualquer CC).
        """
        if ctx.is_privileged or ctx.is_tecnico_ti:
            result = await self.session.execute(
                select(AssociacaoUserEletronico)
            )
            return result.scalars().all()

        gestor_ccs = [
            cc
            for cc, ocup in ctx.ocupacoes.items()
            if ocup in {'Gestor', 'Subgestor'}
        ]

        conditions = [AssociacaoUserEletronico.user_id == ctx.user.id]
        if gestor_ccs:
            conditions.append(
                AssociacaoUserEletronico.eletronico_id.in_(
                    select(Eletronico.id).where(
                        Eletronico.centro_custo.in_(gestor_ccs)
                    )
                )
            )

        result = await self.session.execute(
            select(AssociacaoUserEletronico).where(or_(*conditions))
        )
        return result.scalars().all()

    async def get_by_ids(
        self, user_id: int, eletronico_id: int
    ) -> AssociacaoUserEletronico:
        result = await self.session.execute(
            select(AssociacaoUserEletronico).where(
                AssociacaoUserEletronico.user_id == user_id,
                AssociacaoUserEletronico.eletronico_id == eletronico_id,
            )
        )
        assoc = result.scalar_one_or_none()
        if assoc is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail='Associação usuário-eletrônico não encontrada.',
            )
        return assoc

    async def create(
        self, data: AssociacaoUserEletronicoCreate, ctx: UserContext
    ):
        """
        Autorização per-CC (do eletrônico):
        - Admin / Tecnico_TI → qualquer.
        - Gestor / Subgestor do CC do eletrônico → qualquer usuário.
        - Funcionario do CC do eletrônico → apenas para si mesmo.
        """
        cc = await self._get_eletronico_cc(data.eletronico_id)

        if not (ctx.is_privileged or ctx.is_tecnico_ti):
            ocupacao = ctx.ocupacao_in(cc)
            if ocupacao not in {'Gestor', 'Subgestor', 'Funcionario'}:
                raise HTTPException(
                    status_code=HTTPStatus.FORBIDDEN,
                    detail='Sem permissão neste centro de custo.',
                )
            if (
                ocupacao == 'Funcionario'
                and data.user_id != ctx.user.id
            ):
                raise HTTPException(
                    status_code=HTTPStatus.FORBIDDEN,
                    detail='Funcionário só pode associar para si mesmo.',
                )

        nova = AssociacaoUserEletronico(**data.model_dump())
        try:
            self.session.add(nova)
            await self.session.commit()
            await self.session.refresh(nova)
            return nova
        except IntegrityError:
            await self.session.rollback()
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail='Associação já existe ou usuário/eletrônico inválido.',
            )

    async def delete(self, user_id: int, eletronico_id: int, ctx: UserContext):
        """
        Autorização per-CC (do eletrônico):
        - Admin / Tecnico_TI → qualquer.
        - Gestor / Subgestor do CC do eletrônico → qualquer usuário.
        - Funcionario do CC do eletrônico → apenas as próprias.
        """
        cc = await self._get_eletronico_cc(eletronico_id)

        if not (ctx.is_privileged or ctx.is_tecnico_ti):
            ocupacao = ctx.ocupacao_in(cc)
            if ocupacao not in {'Gestor', 'Subgestor', 'Funcionario'}:
                raise HTTPException(
                    status_code=HTTPStatus.FORBIDDEN,
                    detail='Sem permissão neste centro de custo.',
                )
            if ocupacao == 'Funcionario' and user_id != ctx.user.id:
                raise HTTPException(
                    status_code=HTTPStatus.FORBIDDEN,
                    detail='Funcionário só pode remover as próprias.',
                )

        assoc = await self.get_by_ids(user_id, eletronico_id)
        await self.session.delete(assoc)
        await self.session.commit()
        return assoc
