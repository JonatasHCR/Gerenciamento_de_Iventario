from http import HTTPStatus
from typing import Annotated

from fastapi import Depends
from fastapi.routing import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.engine import EngineApp
from backend.schemas.localizacao import (
    LocalizacaoCreate,
    LocalizacaoList,
    LocalizacaoRead,
    LocalizacaoUpdate,
)
from backend.security.dependencies import Dependencies, UserContext
from backend.service.localizacao import LocalizacaoService

router_localizacoes = APIRouter(
    prefix='/localizacoes', tags=['localizacoes']
)

T_AsyncSession = Annotated[AsyncSession, Depends(EngineApp.get_async_session)]
T_UserContext = Annotated[UserContext, Depends(Dependencies.get_user_context)]


@router_localizacoes.get(
    '/', status_code=HTTPStatus.OK, response_model=LocalizacaoList
)
async def list_locs(
    session: T_AsyncSession,
    ctx: T_UserContext,
):
    service = LocalizacaoService(session)
    locs = await service.list_all(ctx)
    return {'localizacoes': locs}


@router_localizacoes.post(
    '/',
    status_code=HTTPStatus.CREATED,
    response_model=LocalizacaoRead,
)
async def create_loc(
    data: LocalizacaoCreate,
    session: T_AsyncSession,
    ctx: T_UserContext,
):
    service = LocalizacaoService(session)
    return await service.create(data, ctx)


@router_localizacoes.put(
    '/{loc_id}',
    status_code=HTTPStatus.OK,
    response_model=LocalizacaoRead,
)
async def update_loc(
    loc_id: int,
    data: LocalizacaoUpdate,
    session: T_AsyncSession,
    ctx: T_UserContext,
):
    service = LocalizacaoService(session)
    return await service.update(loc_id, data, ctx)


@router_localizacoes.delete(
    '/{loc_id}',
    status_code=HTTPStatus.OK,
    response_model=LocalizacaoRead,
)
async def delete_loc(
    loc_id: int,
    session: T_AsyncSession,
    ctx: T_UserContext,
):
    service = LocalizacaoService(session)
    return await service.delete(loc_id, ctx)
