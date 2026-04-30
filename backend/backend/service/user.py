from http import HTTPStatus

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.model.user import User
from backend.schemas.user import UserCreate
from backend.security.security import Security


class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.security = Security()

    async def get_users(self):

        result = await self.session.execute(select(User))
        return result.scalars().all()

    async def create(self, user: UserCreate):
        existing = await self.session.execute(
            select(User).where(User.email == user.email)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail='Usuário com este email já existe.',
            )
        novo = User(**user.model_dump())
        novo.senha = self.security.get_senha_hash(novo.senha)

        self.session.add(novo)
        await self.session.commit()
        await self.session.refresh(novo)
        return novo

    async def update(self, user_id: int, user: UserCreate):

        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        user_db = result.scalar_one_or_none()
        if user_db is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail='Usuário não encontrado.',
            )

        user.senha = self.security.get_senha_hash(user.senha)

        data = user.model_dump(exclude_unset=True)

        for key, value in data.items():
            setattr(user_db, key, value)

        await self.session.commit()
        await self.session.refresh(user_db)
        return user_db

    async def delete(self, user_id: int):

        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail='Usuário não encontrado.',
            )
        await self.session.delete(user)
        await self.session.commit()

        return user
