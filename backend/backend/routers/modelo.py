from http import HTTPStatus
from typing import Annotated

from fastapi import Depends, Query
from fastapi.routing import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.engine import EngineApp
from backend.schemas.modelo import (
    ModeloCreate,
    ModeloList,
    ModeloRead,
    ModeloUpdate,
)
from backend.security.dependencies import Dependencies, UserContext
from backend.service.modelo import ModeloService

router_modelos = APIRouter(prefix='/modelos', tags=['modelos'])

T_AsyncSession = Annotated[AsyncSession, Depends(EngineApp.get_async_session)]
T_UserContext = Annotated[UserContext, Depends(Dependencies.get_user_context)]


@router_modelos.get(
    '/', status_code=HTTPStatus.OK, response_model=ModeloList
)
async def list_modelos(
    session: T_AsyncSession,
    ctx: T_UserContext,
    marca_id: int | None = Query(
        None, description='Filtra modelos de uma marca específica'
    ),
):
    service = ModeloService(session)
    modelos = await service.list_all(ctx, marca_id=marca_id)
    return {'modelos': modelos}


@router_modelos.post(
    '/',
    status_code=HTTPStatus.CREATED,
    response_model=ModeloRead,
)
async def create_modelo(
    data: ModeloCreate,
    session: T_AsyncSession,
    ctx: T_UserContext,
):
    service = ModeloService(session)
    return await service.create(data, ctx)


@router_modelos.put(
    '/{modelo_id}',
    status_code=HTTPStatus.OK,
    response_model=ModeloRead,
)
async def update_modelo(
    modelo_id: int,
    data: ModeloUpdate,
    session: T_AsyncSession,
    ctx: T_UserContext,
):
    service = ModeloService(session)
    return await service.update(modelo_id, data, ctx)


@router_modelos.delete(
    '/{modelo_id}',
    status_code=HTTPStatus.OK,
    response_model=ModeloRead,
)
async def delete_modelo(
    modelo_id: int,
    session: T_AsyncSession,
    ctx: T_UserContext,
):
    service = ModeloService(session)
    return await service.delete(modelo_id, ctx)
