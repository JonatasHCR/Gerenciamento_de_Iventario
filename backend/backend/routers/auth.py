from http import HTTPStatus
from typing import Annotated

from fastapi import Depends
from fastapi.routing import APIRouter
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.engine import EngineApp
from backend.schemas.token import Token
from backend.schemas.user import UserRead
from backend.security.dependencies import Dependencies
from backend.service.auth import AuthService

router_auth = APIRouter(prefix='/auth', tags=['auth'])

T_AsyncSession = Annotated[AsyncSession, Depends(EngineApp.get_async_session)]
T_OAuth2Form = Annotated[OAuth2PasswordRequestForm, Depends()]
T_CurrentUser = Annotated[UserRead, Depends(Dependencies.get_current_user)]


@router_auth.post('/login', response_model=Token, status_code=HTTPStatus.OK)
async def login(
    form_data: T_OAuth2Form,
    session: T_AsyncSession,
):
    service = AuthService(session)
    return await service.login(form_data)


@router_auth.post(
    '/refresh_token', response_model=Token, status_code=HTTPStatus.OK
)
async def refresh_token(
    current_user: T_CurrentUser,
    session: T_AsyncSession,
):
    service = AuthService(session)
    return await service.refresh_token(current_user)
