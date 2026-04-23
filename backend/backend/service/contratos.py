from http import HTTPStatus

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.model.contratos import Contrato
from backend.schemas.contratos import ContratoCreate


class ContratoService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self):
        result = await self.session.execute(select(Contrato))
        return result.scalars().all()

    async def create(self, contrato: ContratoCreate):
        novo = Contrato(**contrato.model_dump())
        self.session.add(novo)
        await self.session.commit()
        await self.session.refresh(novo)
        return novo

    async def update(self, centro_custo: str, contrato: ContratoCreate):
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

        for key, value in data.items():
            setattr(existing, key, value)

        await self.session.commit()
        await self.session.refresh(existing)
        return existing

    async def delete(self, centro_custo: str):
        result = await self.session.execute(
            select(Contrato).where(Contrato.centro_custo == centro_custo)
        )
        existing = result.scalar_one_or_none()
        if existing is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail='Contrato não encontrado.',
            )
        await self.session.delete(existing)
        await self.session.commit()
