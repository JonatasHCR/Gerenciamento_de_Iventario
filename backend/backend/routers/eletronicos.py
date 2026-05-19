from http import HTTPStatus
from typing import Annotated

from fastapi import Depends, Query
from fastapi.routing import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.engine import EngineApp
from backend.schemas.eletronicos import (
    EletronicoCreate,
    EletronicoList,
    EletronicoRead,
)
from backend.security.dependencies import Dependencies, UserContext
from backend.service.eletronicos import EletronicoService

router_eletronicos = APIRouter(prefix='/eletronicos', tags=['eletronicos'])

T_AsyncSession = Annotated[AsyncSession, Depends(EngineApp.get_async_session)]
T_UserContext = Annotated[UserContext, Depends(Dependencies.get_user_context)]


@router_eletronicos.get(
    '/', status_code=HTTPStatus.OK, response_model=EletronicoList
)
async def get(  # noqa: PLR0913, PLR0917
    session: T_AsyncSession,
    ctx: T_UserContext,
    q: str | None = Query(
        None,
        description=(
            'Busca em nome, série, patrimônio, marca, modelo, '
            'ip, localização'
        ),
    ),
    campo: str = Query(
        'todos',
        description=(
            'Campo de busca: todos, nome, numero_serie, '
            'numero_patrimonio, marca, modelo, ip, localizacao, '
            'responsavel, sem_responsavel'
        ),
    ),
    centro_custo: list[str] | None = Query(None),
    status: list[str] | None = Query(None),
    tipo: list[str] | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
):
    service = EletronicoService(session)
    items, total, pages = await service.get(
        ctx,
        q=q,
        campo=campo,
        centros_custo=centro_custo,
        statuses=status,
        tipos=tipo,
        page=page,
        page_size=page_size,
    )
    return {
        'eletronicos': items,
        'total': total,
        'page': page,
        'page_size': page_size,
        'pages': pages,
    }


@router_eletronicos.post(
    '/', status_code=HTTPStatus.CREATED, response_model=EletronicoRead
)
async def create(
    eletronico: EletronicoCreate,
    session: T_AsyncSession,
    ctx: T_UserContext,
):
    service = EletronicoService(session)
    return await service.create(eletronico, ctx)


@router_eletronicos.put(
    '/{id}', status_code=HTTPStatus.OK, response_model=EletronicoRead
)
async def update(
    id: int,
    eletronico: EletronicoCreate,
    session: T_AsyncSession,
    ctx: T_UserContext,
):
    service = EletronicoService(session)
    return await service.update(id, eletronico, ctx)


@router_eletronicos.delete(
    '/{id}', status_code=HTTPStatus.OK, response_model=EletronicoRead
)
async def delete(
    id: int,
    session: T_AsyncSession,
    ctx: T_UserContext,
):
    service = EletronicoService(session)
    return await service.delete(id, ctx)
