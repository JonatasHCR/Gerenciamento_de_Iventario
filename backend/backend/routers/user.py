from http import HTTPStatus

from fastapi import Depends
from fastapi.routing import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.engine import EngineApp
from backend.schemas.user import UserCreate, UserList, UserRead
from backend.service.user import UserService

router_user = APIRouter(prefix='/users', tags=['users'])


@router_user.get('/', status_code=HTTPStatus.OK, response_model=UserList)
async def get_users(
    session: AsyncSession = Depends(EngineApp.get_async_session),
):
    service = UserService(session)
    users = await service.get_users()
    return {'users': users}


@router_user.post('/', status_code=HTTPStatus.CREATED, response_model=UserRead)
async def create(
    user: UserCreate,
    session: AsyncSession = Depends(EngineApp.get_async_session),
):
    service = UserService(session)
    return await service.create(user)


@router_user.put(
    '/{user_id}', status_code=HTTPStatus.OK, response_model=UserRead
)
async def update(
    user_id: int,
    user: UserCreate,
    session: AsyncSession = Depends(EngineApp.get_async_session),
):
    service = UserService(session)
    return await service.update(user_id, user)


@router_user.delete(
    '/{user_id}', status_code=HTTPStatus.OK, response_model=UserRead
)
async def delete(
    user_id: int,
    session: AsyncSession = Depends(EngineApp.get_async_session),
):
    service = UserService(session)
    return await service.delete(user_id)
