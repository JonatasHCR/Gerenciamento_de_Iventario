from http import HTTPStatus
from typing import Annotated

from fastapi import Depends
from fastapi.routing import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.engine import EngineApp
from backend.schemas.marca import (
    MarcaCreate,
    MarcaList,
    MarcaRead,
    MarcaUpdate,
)
from backend.security.dependencies import Dependencies, UserContext
from backend.service.marca import MarcaService

router_marcas = APIRouter(prefix='/marcas', tags=['marcas'])

T_AsyncSession = Annotated[AsyncSession, Depends(EngineApp.get_async_session)]
T_UserContext = Annotated[UserContext, Depends(Dependencies.get_user_context)]


@router_marcas.get(
    '/', status_code=HTTPStatus.OK, response_model=MarcaList
)
async def list_marcas(
    session: T_AsyncSession,
    ctx: T_UserContext,
):
    service = MarcaService(session)
    marcas = await service.list_all(ctx)
    return {'marcas': marcas}


@router_marcas.post(
    '/',
    status_code=HTTPStatus.CREATED,
    response_model=MarcaRead,
)
async def create_marca(
    data: MarcaCreate,
    session: T_AsyncSession,
    ctx: T_UserContext,
):
    service = MarcaService(session)
    return await service.create(data, ctx)


@router_marcas.put(
    '/{marca_id}',
    status_code=HTTPStatus.OK,
    response_model=MarcaRead,
)
async def update_marca(
    marca_id: int,
    data: MarcaUpdate,
    session: T_AsyncSession,
    ctx: T_UserContext,
):
    service = MarcaService(session)
    return await service.update(marca_id, data, ctx)


@router_marcas.delete(
    '/{marca_id}',
    status_code=HTTPStatus.OK,
    response_model=MarcaRead,
)
async def delete_marca(
    marca_id: int,
    session: T_AsyncSession,
    ctx: T_UserContext,
):
    service = MarcaService(session)
    return await service.delete(marca_id, ctx)
