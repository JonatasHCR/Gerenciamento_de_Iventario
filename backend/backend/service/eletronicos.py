from http import HTTPStatus

from fastapi import HTTPException
from sqlalchemy import Select, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.pagination import paginate
from backend.model.associacao_user_eletronico import AssociacaoUserEletronico
from backend.model.eletronicos import Eletronico
from backend.model.user import User
from backend.schemas.eletronicos import EletronicoCreate
from backend.security.dependencies import UserContext
from backend.service.tipo_eletronico import TipoEletronicoService

CAMPOS_BUSCA_VALIDOS = {
    'todos',
    'nome',
    'numero_serie',
    'numero_patrimonio',
    'marca',
    'modelo',
    'ip',
    'localizacao',
    'responsavel',
    'sem_responsavel',
}


class EletronicoService:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _base_query(self, ctx: UserContext) -> Select | None:  # noqa: PLR6301

        """
        Retorna o Select base filtrado por **ocupação per-CC**:
        - Admin/TI → todos.
        - Para cada CC em ocupacoes:
          - Gestor/Subgestor → todos os eletrônicos daquele CC.
          - Funcionario → apenas os associados diretamente a ele
            naquele CC.

        Note: o `tipo` global do usuário não importa aqui — quem manda
        é a ocupação em cada CC. Um usuário com `tipo='Gestor'` mas
        que é Funcionario num CC vê só os próprios daquele CC.
        """
        if ctx.is_privileged or ctx.is_tecnico_ti:
            return select(Eletronico)

        gestor_subgestor_ccs = [
            cc
            for cc, ocup in ctx.ocupacoes.items()
            if ocup in {'Gestor', 'Subgestor'}
        ]
        funcionario_ccs = [
            cc
            for cc, ocup in ctx.ocupacoes.items()
            if ocup == 'Funcionario'
        ]

        if not gestor_subgestor_ccs and not funcionario_ccs:
            return None

        conditions = []
        if gestor_subgestor_ccs:
            conditions.append(
                Eletronico.centro_custo.in_(gestor_subgestor_ccs)
            )
        if funcionario_ccs:
            # eletrônicos em CCs onde é Funcionario, associados a ele
            sub = (
                select(AssociacaoUserEletronico.eletronico_id)
                .where(AssociacaoUserEletronico.user_id == ctx.user.id)
            )
            conditions.append(
                Eletronico.centro_custo.in_(funcionario_ccs)
                & Eletronico.id.in_(sub)
            )

        return select(Eletronico).where(or_(*conditions))

    async def get(  # noqa: PLR0913
        self,
        ctx: UserContext,
        *,
        q: str | None = None,
        campo: str = 'todos',
        centros_custo: list[str] | None = None,
        statuses: list[str] | None = None,
        tipos: list[str] | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[Eletronico], int, int]:
        """
        Lista paginada de eletrônicos.
        Retorna (items, total, pages).
        """
        if campo not in CAMPOS_BUSCA_VALIDOS:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail=f'Campo de busca inválido: {campo}',
            )

        query = self._base_query(ctx)
        if query is None:
            return [], 0, 1

        like = f'%{q}%' if q else None

        col_map = {
            'nome': Eletronico.nome,
            'numero_serie': Eletronico.numero_serie,
            'numero_patrimonio': Eletronico.numero_patrimonio,
            'marca': Eletronico.marca,
            'modelo': Eletronico.modelo,
            'ip': Eletronico.ip,
            'localizacao': Eletronico.localizacao,
        }

        if campo == 'sem_responsavel':
            sub_com_resp = select(AssociacaoUserEletronico.eletronico_id)
            query = query.where(~Eletronico.id.in_(sub_com_resp))
        elif campo == 'responsavel':
            sub = (
                select(AssociacaoUserEletronico.eletronico_id)
                .join(User, User.id == AssociacaoUserEletronico.user_id)
            )
            if like:
                sub = sub.where(User.nome.ilike(like))
            query = query.where(Eletronico.id.in_(sub))
        elif campo in col_map and like:
            query = query.where(col_map[campo].ilike(like))
        elif campo == 'todos' and like:
            query = query.where(
                or_(
                    Eletronico.nome.ilike(like),
                    Eletronico.numero_serie.ilike(like),
                    Eletronico.numero_patrimonio.ilike(like),
                    Eletronico.marca.ilike(like),
                    Eletronico.modelo.ilike(like),
                    Eletronico.ip.ilike(like),
                    Eletronico.localizacao.ilike(like),
                )
            )

        if centros_custo:
            query = query.where(
                Eletronico.centro_custo.in_(centros_custo)
            )
        if statuses:
            query = query.where(Eletronico.status.in_(statuses))
        if tipos:
            query = query.where(Eletronico.tipo.in_(tipos))

        query = query.order_by(Eletronico.id.desc())

        items, total, pages = await paginate(
            self.session, query, page, page_size
        )
        return items, total, pages

    async def _get_by_id(self, eletronico_id: int) -> Eletronico:
        result = await self.session.execute(
            select(Eletronico).where(Eletronico.id == eletronico_id)
        )
        eletronico = result.scalar_one_or_none()
        if eletronico is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail='Eletrônico não encontrado.',
            )
        return eletronico

    async def _assert_ownership(
        self, eletronico: Eletronico, ctx: UserContext
    ):
        """
        Autorização per-CC sobre o eletrônico:
        - Admin / Tecnico_TI → sem restrição.
        - Gestor / Subgestor do CC do eletrônico → autorizado.
        - Funcionário do CC do eletrônico → autorizado APENAS se o
          eletrônico está associado diretamente a ele.
        - Demais (não pertence ao CC) → 403.
        """
        if ctx.is_privileged or ctx.is_tecnico_ti:
            return

        ocupacao = ctx.ocupacao_in(eletronico.centro_custo)
        if ocupacao in {'Gestor', 'Subgestor'}:
            return

        if ocupacao == 'Funcionario':
            assoc = await self.session.execute(
                select(AssociacaoUserEletronico).where(
                    AssociacaoUserEletronico.user_id == ctx.user.id,
                    AssociacaoUserEletronico.eletronico_id == eletronico.id,
                )
            )
            if assoc.scalar_one_or_none() is None:
                raise HTTPException(
                    status_code=HTTPStatus.FORBIDDEN,
                    detail=(
                        'Funcionário só pode operar nos próprios '
                        'eletrônicos.'
                    ),
                )
            return

        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail='Sem permissão neste centro de custo.',
        )

    async def create(self, eletronico: EletronicoCreate, ctx: UserContext):
        """
        Criação per-CC:
        - Admin / Tecnico_TI → qualquer CC.
        - Gestor / Subgestor do CC → cria; associação livre depois.
        - Funcionário do CC → cria, mas o eletrônico é
          auto-associado a ele (vira "do funcionário").
        """
        is_full = ctx.is_privileged or ctx.is_tecnico_ti
        ocupacao = ctx.ocupacao_in(eletronico.centro_custo)

        if not is_full and ocupacao not in {
            'Gestor', 'Subgestor', 'Funcionario',
        }:
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail='Sem permissão neste centro de custo.',
            )

        # Valida o tipo contra o catálogo dinâmico
        await TipoEletronicoService(self.session).assert_nome_valido(
            eletronico.tipo
        )

        novo = Eletronico(**eletronico.model_dump())
        try:
            self.session.add(novo)
            await self.session.flush()
            if not is_full and ocupacao == 'Funcionario':
                self.session.add(
                    AssociacaoUserEletronico(
                        user_id=ctx.user.id,
                        eletronico_id=novo.id,
                    )
                )
            await self.session.commit()
            await self.session.refresh(novo)
            return novo
        except IntegrityError:
            await self.session.rollback()
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail='ip,numero de série ou numero de patrimonio já existe',
            )

    async def update(
        self,
        eletronico_id: int,
        eletronico: EletronicoCreate,
        ctx: UserContext,
    ):
        existing = await self._get_by_id(eletronico_id)
        await self._assert_ownership(existing, ctx)

        # Valida o tipo contra o catálogo dinâmico
        if eletronico.tipo != existing.tipo:
            await TipoEletronicoService(self.session).assert_nome_valido(
                eletronico.tipo
            )

        try:
            data = eletronico.model_dump(exclude_unset=True)
            for key, value in data.items():
                setattr(existing, key, value)
            await self.session.commit()
            await self.session.refresh(existing)
            return existing
        except IntegrityError:
            await self.session.rollback()
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail='ip,numero de série ou numero de patrimonio já existe',
            )

    async def delete(self, eletronico_id: int, ctx: UserContext):
        eletronico = await self._get_by_id(eletronico_id)
        await self._assert_ownership(eletronico, ctx)
        await self.session.delete(eletronico)
        await self.session.commit()
        return eletronico
