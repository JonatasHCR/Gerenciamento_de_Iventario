from http import HTTPStatus

from fastapi import HTTPException
from sqlalchemy import select, update as sa_update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.model.eletronicos import Eletronico
from backend.model.localizacao import Localizacao
from backend.schemas.localizacao import (
    LocalizacaoCreate,
    LocalizacaoUpdate,
)
from backend.security.dependencies import UserContext


class LocalizacaoService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_all(
        self, ctx: UserContext
    ) -> list[Localizacao]:
        del ctx  # leitura aberta a qualquer autenticado
        result = await self.session.execute(
            select(Localizacao).order_by(Localizacao.nome)
        )
        return list(result.scalars().all())

    async def _get_by_id(self, loc_id: int) -> Localizacao:
        result = await self.session.execute(
            select(Localizacao).where(Localizacao.id == loc_id)
        )
        loc = result.scalar_one_or_none()
        if loc is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail='Localização não encontrada.',
            )
        return loc

    async def create(
        self, data: LocalizacaoCreate, ctx: UserContext
    ) -> Localizacao:
        """Qualquer usuário autenticado pode criar localização."""
        del ctx
        nova = Localizacao(
            nome=data.nome.strip(),
            descricao=data.descricao,
        )
        try:
            self.session.add(nova)
            await self.session.commit()
            await self.session.refresh(nova)
            return nova
        except IntegrityError:
            await self.session.rollback()
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail='Já existe uma localização com esse nome.',
            )

    async def update(
        self,
        loc_id: int,
        data: LocalizacaoUpdate,
        ctx: UserContext,
    ) -> Localizacao:
        """Apenas Admin pode editar."""
        if not ctx.is_privileged:
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail='Apenas Admin pode editar localizações.',
            )
        loc = await self._get_by_id(loc_id)
        nome_antigo = loc.nome
        payload = data.model_dump(exclude_unset=True)
        if 'nome' in payload:
            payload['nome'] = payload['nome'].strip()

        for k, v in payload.items():
            setattr(loc, k, v)

        # Cascade rename no campo `localizacao` dos eletrônicos
        if (
            'nome' in payload
            and payload['nome'] != nome_antigo
        ):
            await self.session.execute(
                sa_update(Eletronico)
                .where(Eletronico.localizacao == nome_antigo)
                .values(localizacao=payload['nome'])
                .execution_options(synchronize_session='fetch')
            )

        try:
            await self.session.commit()
            await self.session.refresh(loc)
            return loc
        except IntegrityError:
            await self.session.rollback()
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail='Já existe uma localização com esse nome.',
            )

    async def delete(
        self, loc_id: int, ctx: UserContext
    ) -> Localizacao:
        """Apenas Admin pode excluir."""
        if not ctx.is_privileged:
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail='Apenas Admin pode remover localizações.',
            )
        loc = await self._get_by_id(loc_id)
        await self.session.delete(loc)
        await self.session.commit()
        return loc
