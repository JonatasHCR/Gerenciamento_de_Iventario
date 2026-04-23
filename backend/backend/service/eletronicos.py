from http import HTTPStatus

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.model.eletronicos import Eletronico
from backend.schemas.eletronicos import EletronicoCreate


class EletronicoService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self):
        result = await self.session.execute(select(Eletronico))
        return result.scalars().all()

    async def create(self, eletronico: EletronicoCreate):
        novo = Eletronico(**eletronico.model_dump())
        self.session.add(novo)
        await self.session.commit()
        await self.session.refresh(novo)
        return novo

    async def update(self, eletronico_id: int, eletronico: EletronicoCreate):
        result = await self.session.execute(
            select(Eletronico).where(Eletronico.id == eletronico_id)
        )
        existing = result.scalar_one_or_none()
        if existing is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail='Eletrônico não encontrado.',
            )

        data = eletronico.model_dump(exclude_unset=True)

        for key, value in data.items():
            setattr(existing, key, value)

        await self.session.commit()
        await self.session.refresh(existing)
        return existing

    async def delete(self, eletronico_id: int):
        result = await self.session.execute(
            select(Eletronico).where(Eletronico.id == eletronico_id)
        )
        existing = result.scalar_one_or_none()
        if existing is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail='Eletrônico não encontrado.',
            )
        await self.session.delete(existing)
        await self.session.commit()
