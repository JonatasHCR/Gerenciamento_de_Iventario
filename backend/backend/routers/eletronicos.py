from http import HTTPStatus
from typing import Annotated

from fastapi import Depends
from fastapi.routing import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.engine import EngineApp
from backend.schemas.eletronicos import (
    EletronicoCreate,
    EletronicoList,
    EletronicoRead,
)
from backend.schemas.user import UserRead
from backend.security.dependencies import Dependencies
from backend.service.eletronicos import EletronicoService

router_eletronicos = APIRouter(prefix='/eletronicos', tags=['eletronicos'])

T_AsyncSession = Annotated[AsyncSession, Depends(EngineApp.get_async_session)]
T_CurrentUser = Annotated[UserRead, Depends(Dependencies.get_current_user)]


@router_eletronicos.get(
    '/', status_code=HTTPStatus.OK, response_model=EletronicoList
)
async def get(
    session: T_AsyncSession,
    current_user: T_CurrentUser,
):
    service = EletronicoService(session)
    eletronicos = await service.get()
    return {'eletronicos': eletronicos}


@router_eletronicos.post(
    '/', status_code=HTTPStatus.CREATED, response_model=EletronicoRead
)
async def create(
    eletronico: EletronicoCreate,
    session: T_AsyncSession,
    current_user: T_CurrentUser,
):
    service = EletronicoService(session)
    return await service.create(eletronico)


@router_eletronicos.put(
    '/{id}', status_code=HTTPStatus.OK, response_model=EletronicoRead
)
async def update(
    id: int,
    eletronico: EletronicoCreate,
    session: T_AsyncSession,
    current_user: T_CurrentUser,
):
    service = EletronicoService(session)
    return await service.update(id, eletronico)


@router_eletronicos.delete(
    '/{id}', status_code=HTTPStatus.OK, response_model=EletronicoRead
)
async def delete(
    id: int,
    session: T_AsyncSession,
    current_user: T_CurrentUser,
):
    service = EletronicoService(session)
    return await service.delete(id)
