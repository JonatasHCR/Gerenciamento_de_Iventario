from http import HTTPStatus

from fastapi import Depends
from fastapi.routing import APIRouter
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.engine import EngineApp
from backend.schemas.token import Token
from backend.service.auth import AuthService

router_auth = APIRouter(prefix='/auth', tags=['auth'])


@router_auth.post('/login', response_model=Token, status_code=HTTPStatus.OK)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(EngineApp.get_async_session),
):
    service = AuthService(session)
    return await service.login(form_data)
