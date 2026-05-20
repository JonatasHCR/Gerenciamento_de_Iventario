from http import HTTPStatus
from typing import Annotated

from fastapi import Depends, Query
from fastapi.routing import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.engine import EngineApp
from backend.schemas.tipo_eletronico import (
    TipoEletronicoCreate,
    TipoEletronicoList,
    TipoEletronicoRead,
    TipoEletronicoUpdate,
)
from backend.security.dependencies import Dependencies, UserContext
from backend.service.tipo_eletronico import TipoEletronicoService

router_tipos_eletronico = APIRouter(
    prefix='/tipos-eletronico', tags=['tipos-eletronico']
)

T_AsyncSession = Annotated[AsyncSession, Depends(EngineApp.get_async_session)]
T_UserContext = Annotated[UserContext, Depends(Dependencies.get_user_context)]


@router_tipos_eletronico.get(
    '/', status_code=HTTPStatus.OK, response_model=TipoEletronicoList
)
async def list_tipos(
    session: T_AsyncSession,
    ctx: T_UserContext,
    apenas_ativos: bool = Query(
        False,
        description='Quando true, esconde tipos com ativo=False',
    ),
):
    service = TipoEletronicoService(session)
    tipos = await service.list_all(ctx, apenas_ativos=apenas_ativos)
    return {'tipos': tipos}


@router_tipos_eletronico.post(
    '/',
    status_code=HTTPStatus.CREATED,
    response_model=TipoEletronicoRead,
)
async def create_tipo(
    data: TipoEletronicoCreate,
    session: T_AsyncSession,
    ctx: T_UserContext,
):
    service = TipoEletronicoService(session)
    return await service.create(data, ctx)


@router_tipos_eletronico.put(
    '/{tipo_id}',
    status_code=HTTPStatus.OK,
    response_model=TipoEletronicoRead,
)
async def update_tipo(
    tipo_id: int,
    data: TipoEletronicoUpdate,
    session: T_AsyncSession,
    ctx: T_UserContext,
):
    service = TipoEletronicoService(session)
    return await service.update(tipo_id, data, ctx)


@router_tipos_eletronico.delete(
    '/{tipo_id}',
    status_code=HTTPStatus.OK,
    response_model=TipoEletronicoRead,
)
async def delete_tipo(
    tipo_id: int,
    session: T_AsyncSession,
    ctx: T_UserContext,
):
    service = TipoEletronicoService(session)
    return await service.delete(tipo_id, ctx)
