from http import HTTPStatus
from typing import Annotated

from fastapi import Depends
from fastapi.routing import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.engine import EngineApp
from backend.schemas.user import UserCreate, UserList, UserRead, UserUpdate
from backend.security.dependencies import Dependencies, UserContext
from backend.service.user import UserService

router_user = APIRouter(prefix='/users', tags=['users'])

T_AsyncSession = Annotated[AsyncSession, Depends(EngineApp.get_async_session)]
T_UserContext = Annotated[UserContext, Depends(Dependencies.get_user_context)]


@router_user.get('/', status_code=HTTPStatus.OK, response_model=UserList)
async def get_users(
    session: T_AsyncSession,
    ctx: T_UserContext,
):
    service = UserService(session)
    users = await service.get_users(ctx)
    return {'users': users}


@router_user.post('/', status_code=HTTPStatus.CREATED, response_model=UserRead)
async def create(
    user: UserCreate,
    session: T_AsyncSession,
):
    """
    Auto-registro público: cria o usuário sempre como Funcionario.
    Admin/TI devem usar o endpoint autenticado
    """
    service = UserService(session)
    return await service.create(user, ctx=None)


@router_user.post(
    '/admin',
    status_code=HTTPStatus.CREATED,
    response_model=UserRead,
)
async def create_admin(
    user: UserCreate,
    session: T_AsyncSession,
    ctx: T_UserContext,
):
    """Criação de usuário com tipo específico"""
    service = UserService(session)
    return await service.create(user, ctx=ctx)


@router_user.put(
    '/{user_id}', status_code=HTTPStatus.OK, response_model=UserRead
)
async def update(
    user_id: int,
    user: UserUpdate,
    session: T_AsyncSession,
    ctx: T_UserContext,
):
    service = UserService(session)
    return await service.update(user_id, user, ctx)


@router_user.delete(
    '/{user_id}', status_code=HTTPStatus.OK, response_model=UserRead
)
async def delete(
    user_id: int,
    session: T_AsyncSession,
    ctx: T_UserContext,
):
    service = UserService(session)
    return await service.delete(user_id, ctx)
