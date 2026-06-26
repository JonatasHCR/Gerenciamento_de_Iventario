from http import HTTPStatus

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy import update as sa_update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.model.eletronicos import Eletronico
from backend.model.marca import Marca
from backend.schemas.marca import MarcaCreate, MarcaUpdate
from backend.security.dependencies import UserContext


class MarcaService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_all(self, ctx: UserContext) -> list[Marca]:
        del ctx  # leitura aberta a qualquer autenticado
        result = await self.session.execute(
            select(Marca).order_by(Marca.nome)
        )
        return list(result.scalars().all())

    async def _get_by_id(self, marca_id: int) -> Marca:
        result = await self.session.execute(
            select(Marca).where(Marca.id == marca_id)
        )
        marca = result.scalar_one_or_none()
        if marca is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail='Marca não encontrada.',
            )
        return marca

    async def create(
        self, data: MarcaCreate, ctx: UserContext
    ) -> Marca:
        """Qualquer usuário autenticado pode criar marca."""
        del ctx
        nova = Marca(nome=data.nome.strip())
        try:
            self.session.add(nova)
            await self.session.commit()
            await self.session.refresh(nova)
            return nova
        except IntegrityError:
            await self.session.rollback()
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail='Já existe uma marca com esse nome.',
            )

    async def update(
        self,
        marca_id: int,
        data: MarcaUpdate,
        ctx: UserContext,
    ) -> Marca:
        """Apenas Admin pode editar."""
        if not ctx.is_privileged:
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail='Apenas Admin pode editar marcas.',
            )
        marca = await self._get_by_id(marca_id)
        nome_antigo = marca.nome
        payload = data.model_dump(exclude_unset=True)
        if 'nome' in payload:
            payload['nome'] = payload['nome'].strip()

        try:
            for k, v in payload.items():
                setattr(marca, k, v)

            # Cascade rename no campo `marca` dos eletrônicos
            if (
                'nome' in payload
                and payload['nome'] != nome_antigo
            ):
                await self.session.execute(
                    sa_update(Eletronico)
                    .where(Eletronico.marca == nome_antigo)
                    .values(marca=payload['nome'])
                    .execution_options(synchronize_session='fetch')
                )

            await self.session.commit()
            await self.session.refresh(marca)
            return marca
        except IntegrityError:
            await self.session.rollback()
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail='Já existe uma marca com esse nome.',
            )

    async def delete(
        self, marca_id: int, ctx: UserContext
    ) -> Marca:
        """Apenas Admin pode excluir (remove os modelos em cascata)."""
        if not ctx.is_privileged:
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail='Apenas Admin pode remover marcas.',
            )
        marca = await self._get_by_id(marca_id)
        await self.session.delete(marca)
        await self.session.commit()
        return marca
