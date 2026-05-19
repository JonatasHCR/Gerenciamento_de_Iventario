from http import HTTPStatus
from typing import Annotated

from fastapi import Depends
from fastapi.routing import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.engine import EngineApp
from backend.schemas.cessao import (
    CessaoCreate,
    CessaoDevolverRequest,
    CessaoList,
    CessaoRead,
    MarcarVistosResponse,
    RecebimentosPendentesGestor,
)
from backend.security.dependencies import Dependencies, UserContext
from backend.service.cessao import CessaoService

router_cessao = APIRouter(prefix='/cessoes', tags=['cessoes'])

T_AsyncSession = Annotated[AsyncSession, Depends(EngineApp.get_async_session)]
T_UserContext = Annotated[UserContext, Depends(Dependencies.get_user_context)]


@router_cessao.get(
    '/', status_code=HTTPStatus.OK, response_model=CessaoList
)
async def get_all(session: T_AsyncSession, ctx: T_UserContext):
    service = CessaoService(session)
    return {'cessoes': await service.list_all(ctx)}


@router_cessao.post(
    '/', status_code=HTTPStatus.CREATED, response_model=CessaoRead
)
async def create(
    data: CessaoCreate, session: T_AsyncSession, ctx: T_UserContext
):
    service = CessaoService(session)
    return await service.create(data, ctx)


# Rotas com prefixo fixo devem vir ANTES de `/{cessao_id}` para evitar
# que o FastAPI tente fazer coerção do path-param int.
@router_cessao.get(
    '/recebimentos/pendentes-gestor',
    status_code=HTTPStatus.OK,
    response_model=RecebimentosPendentesGestor,
)
async def recebimentos_pendentes_gestor(
    session: T_AsyncSession,
    ctx: T_UserContext,
):
    service = CessaoService(session)
    return await service.recebimentos_pendentes_gestor(ctx)


@router_cessao.put(
    '/recebimentos/visto',
    status_code=HTTPStatus.OK,
    response_model=MarcarVistosResponse,
)
async def marcar_recebimentos_vistos(
    session: T_AsyncSession,
    ctx: T_UserContext,
):
    service = CessaoService(session)
    return await service.marcar_recebimentos_vistos(ctx)


@router_cessao.get(
    '/{cessao_id}', status_code=HTTPStatus.OK, response_model=CessaoRead
)
async def get_one(
    cessao_id: int, session: T_AsyncSession, ctx: T_UserContext
):
    service = CessaoService(session)
    return await service.get_by_id(cessao_id, ctx)


@router_cessao.put(
    '/{cessao_id}/devolver',
    status_code=HTTPStatus.OK,
    response_model=CessaoRead,
)
async def devolver(
    cessao_id: int,
    data: CessaoDevolverRequest,
    session: T_AsyncSession,
    ctx: T_UserContext,
):
    service = CessaoService(session)
    return await service.devolver(cessao_id, ctx, data)


@router_cessao.delete(
    '/{cessao_id}',
    status_code=HTTPStatus.OK,
    response_model=CessaoRead,
)
async def delete(
    cessao_id: int,
    session: T_AsyncSession,
    ctx: T_UserContext,
):
    service = CessaoService(session)
    return await service.delete(cessao_id, ctx)
