from http import HTTPStatus

from fastapi import HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.model.user import User
from backend.security.security import Security


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.security = Security()

    async def login(self, form_data: OAuth2PasswordRequestForm):
        result = await self.session.execute(
            select(User).where(User.email == form_data.username)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail='Email ou senha inválidos.',
            )

        if not self.security.verify_senha(form_data.password, user.senha):
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail='Email ou senha inválidos.',
            )

        access_token = self.security.get_access_token(
            data={'sub': str(user.email)}
        )

        return {'access_token': access_token, 'token_type': 'Bearer'}

    async def refresh_token(self, current_user):

        user = current_user

        access_token = self.security.get_access_token(
            data={'sub': str(user.email)}
        )

        return {'access_token': access_token, 'token_type': 'Bearer'}
