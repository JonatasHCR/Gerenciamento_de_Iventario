from http import HTTPStatus
from typing import Annotated

from fastapi import Depends
from fastapi.routing import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.engine import EngineApp
from backend.schemas.associacoes import (
    AssociacaoUserContratoCreate,
    AssociacaoUserContratoList,
    AssociacaoUserContratoRead,
    AssociacaoUserEletronicoCreate,
    AssociacaoUserEletronicoList,
    AssociacaoUserEletronicoRead,
)
from backend.security.dependencies import Dependencies, UserContext
from backend.service.associacoes import (
    AssociacaoUserContratoService,
    AssociacaoUserEletronicoService,
)

router_assoc_contrato = APIRouter(
    prefix='/associacoes/contratos',
    tags=['associacoes-contratos'],
)

router_assoc_eletronico = APIRouter(
    prefix='/associacoes/eletronicos',
    tags=['associacoes-eletronicos'],
)

T_AsyncSession = Annotated[AsyncSession, Depends(EngineApp.get_async_session)]
T_UserContext = Annotated[UserContext, Depends(Dependencies.get_user_context)]


# ─── AssociacaoUserContrato


@router_assoc_contrato.get(
    '/',
    status_code=HTTPStatus.OK,
    response_model=AssociacaoUserContratoList,
)
async def get_associacoes_contrato(
    session: T_AsyncSession,
    ctx: T_UserContext,
):
    service = AssociacaoUserContratoService(session)
    associacoes = await service.get(ctx)
    return {'associacoes': associacoes}


@router_assoc_contrato.post(
    '/',
    status_code=HTTPStatus.CREATED,
    response_model=AssociacaoUserContratoRead,
)
async def create_associacao_contrato(
    data: AssociacaoUserContratoCreate,
    session: T_AsyncSession,
    ctx: T_UserContext,
):
    service = AssociacaoUserContratoService(session)
    return await service.create(data, ctx)


@router_assoc_contrato.put(
    '/{user_id}/{centro_custo}',
    status_code=HTTPStatus.OK,
    response_model=AssociacaoUserContratoRead,
)
async def update_associacao_contrato(
    user_id: int,
    centro_custo: str,
    data: AssociacaoUserContratoCreate,
    session: T_AsyncSession,
    ctx: T_UserContext,
):
    service = AssociacaoUserContratoService(session)
    return await service.update(user_id, centro_custo, data, ctx)


@router_assoc_contrato.delete(
    '/{user_id}/{centro_custo}',
    status_code=HTTPStatus.OK,
    response_model=AssociacaoUserContratoRead,
)
async def delete_associacao_contrato(
    user_id: int,
    centro_custo: str,
    session: T_AsyncSession,
    ctx: T_UserContext,
):
    service = AssociacaoUserContratoService(session)
    return await service.delete(user_id, centro_custo, ctx)


# ─── AssociacaoUserEletronico


@router_assoc_eletronico.get(
    '/',
    status_code=HTTPStatus.OK,
    response_model=AssociacaoUserEletronicoList,
)
async def get_associacoes_eletronico(
    session: T_AsyncSession,
    ctx: T_UserContext,
):
    service = AssociacaoUserEletronicoService(session)
    associacoes = await service.get(ctx)
    return {'associacoes': associacoes}


@router_assoc_eletronico.post(
    '/',
    status_code=HTTPStatus.CREATED,
    response_model=AssociacaoUserEletronicoRead,
)
async def create_associacao_eletronico(
    data: AssociacaoUserEletronicoCreate,
    session: T_AsyncSession,
    ctx: T_UserContext,
):
    service = AssociacaoUserEletronicoService(session)
    return await service.create(data, ctx)


@router_assoc_eletronico.delete(
    '/{user_id}/{eletronico_id}',
    status_code=HTTPStatus.OK,
    response_model=AssociacaoUserEletronicoRead,
)
async def delete_associacao_eletronico(
    user_id: int,
    eletronico_id: int,
    session: T_AsyncSession,
    ctx: T_UserContext,
):
    service = AssociacaoUserEletronicoService(session)
    return await service.delete(user_id, eletronico_id, ctx)
