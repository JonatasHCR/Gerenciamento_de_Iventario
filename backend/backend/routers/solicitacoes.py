from http import HTTPStatus
from typing import Annotated

from fastapi import Depends
from fastapi.routing import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.engine import EngineApp
from backend.schemas.solicitacoes import (
    SolicitacaoCargoInicialCreate,
    SolicitacaoCessaoCreate,
    SolicitacaoConviteCCCreate,
    SolicitacaoEntradaCCCreate,
    SolicitacaoList,
    SolicitacaoRead,
)
from backend.security.dependencies import Dependencies, UserContext
from backend.service.solicitacoes import SolicitacaoService

router_solicitacoes = APIRouter(
    prefix='/solicitacoes', tags=['solicitacoes']
)

T_AsyncSession = Annotated[AsyncSession, Depends(EngineApp.get_async_session)]
T_UserContext = Annotated[UserContext, Depends(Dependencies.get_user_context)]


@router_solicitacoes.get(
    '/', status_code=HTTPStatus.OK, response_model=SolicitacaoList
)
async def get(session: T_AsyncSession, ctx: T_UserContext):
    service = SolicitacaoService(session)
    return {'solicitacoes': await service.get(ctx)}


@router_solicitacoes.post(
    '/entrada-cc',
    status_code=HTTPStatus.CREATED,
    response_model=SolicitacaoRead,
)
async def create_entrada_cc(
    data: SolicitacaoEntradaCCCreate,
    session: T_AsyncSession,
    ctx: T_UserContext,
):
    service = SolicitacaoService(session)
    return await service.create_entrada_cc(data, ctx)


@router_solicitacoes.post(
    '/convite-cc',
    status_code=HTTPStatus.CREATED,
    response_model=SolicitacaoRead,
)
async def create_convite_cc(
    data: SolicitacaoConviteCCCreate,
    session: T_AsyncSession,
    ctx: T_UserContext,
):
    service = SolicitacaoService(session)
    return await service.create_convite_cc(data, ctx)


@router_solicitacoes.post(
    '/cargo-inicial',
    status_code=HTTPStatus.CREATED,
    response_model=SolicitacaoRead,
)
async def create_cargo_inicial(
    data: SolicitacaoCargoInicialCreate,
    session: T_AsyncSession,
    ctx: T_UserContext,
):
    service = SolicitacaoService(session)
    return await service.create_cargo_inicial(data, ctx)


@router_solicitacoes.post(
    '/cessao',
    status_code=HTTPStatus.CREATED,
    response_model=SolicitacaoRead,
)
async def create_cessao(
    data: SolicitacaoCessaoCreate,
    session: T_AsyncSession,
    ctx: T_UserContext,
):
    service = SolicitacaoService(session)
    return await service.create_cessao(data, ctx)


@router_solicitacoes.put(
    '/{solicitacao_id}/aprovar',
    status_code=HTTPStatus.OK,
    response_model=SolicitacaoRead,
)
async def aprovar(
    solicitacao_id: int,
    session: T_AsyncSession,
    ctx: T_UserContext,
):
    service = SolicitacaoService(session)
    return await service.aprovar(solicitacao_id, ctx)


@router_solicitacoes.put(
    '/{solicitacao_id}/rejeitar',
    status_code=HTTPStatus.OK,
    response_model=SolicitacaoRead,
)
async def rejeitar(
    solicitacao_id: int,
    session: T_AsyncSession,
    ctx: T_UserContext,
):
    service = SolicitacaoService(session)
    return await service.rejeitar(solicitacao_id, ctx)


@router_solicitacoes.delete(
    '/{solicitacao_id}',
    status_code=HTTPStatus.OK,
    response_model=SolicitacaoRead,
)
async def cancelar(
    solicitacao_id: int,
    session: T_AsyncSession,
    ctx: T_UserContext,
):
    service = SolicitacaoService(session)
    return await service.cancelar(solicitacao_id, ctx)
