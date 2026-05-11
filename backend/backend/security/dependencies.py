from http import HTTPStatus

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jwt import DecodeError, ExpiredSignatureError, decode
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.engine import EngineApp
from backend.core.settings import Settings
from backend.model.user import User


class Dependencies:
    @staticmethod
    async def get_current_user(
        token: str = Depends(OAuth2PasswordBearer(tokenUrl='auth/login')),
        session: AsyncSession = Depends(EngineApp.get_async_session),
    ):
        try:
            payload = decode(
                token,
                Settings().SECRET_KEY,
                algorithms=[Settings().ALGORITHM],
            )
        except (DecodeError, ExpiredSignatureError):
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail='Credenciais inválidas.',
                headers={'WWW-Authenticate': 'Bearer'},
            )

        email = payload.get('sub')
        if not email:
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail='Credenciais inválidas.',
            )

        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail='Credenciais inválidas.',
            )

        return user

    @staticmethod
    def role_required(*roles: str):
        async def dependency(
            current_user: User = Depends(Dependencies.get_current_user),
        ):
            if current_user.tipo not in set(roles):
                raise HTTPException(
                    status_code=HTTPStatus.FORBIDDEN,
                    detail='Sem permissão',
                )
            return current_user

        return dependency
