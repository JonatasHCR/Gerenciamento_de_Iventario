from http import HTTPStatus

from fastapi import Depends
from fastapi.routing import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.engine import EngineApp
from backend.schemas.eletronicos import (
    EletronicoCreate,
    EletronicoList,
    EletronicoRead,
)
from backend.security.dependencies import Dependencies
from backend.service.eletronicos import EletronicoService

router_eletronicos = APIRouter(prefix='/eletronicos', tags=['eletronicos'])


@router_eletronicos.get(
    '/', status_code=HTTPStatus.OK, response_model=EletronicoList
)
async def get(
    session: AsyncSession = Depends(EngineApp.get_async_session),
    current_user=Depends(Dependencies.get_current_user),
):
    service = EletronicoService(session)
    eletronicos = await service.get()
    return {'eletronicos': eletronicos}


@router_eletronicos.post(
    '/', status_code=HTTPStatus.CREATED, response_model=EletronicoRead
)
async def create(
    eletronico: EletronicoCreate,
    session: AsyncSession = Depends(EngineApp.get_async_session),
    current_user=Depends(Dependencies.get_current_user),
):
    service = EletronicoService(session)
    return await service.create(eletronico)


@router_eletronicos.put(
    '/{id}', status_code=HTTPStatus.OK, response_model=EletronicoRead
)
async def update(
    id: int,
    eletronico: EletronicoCreate,
    session: AsyncSession = Depends(EngineApp.get_async_session),
    current_user=Depends(Dependencies.get_current_user),
):
    service = EletronicoService(session)
    return await service.update(id, eletronico)


@router_eletronicos.delete(
    '/{id}', status_code=HTTPStatus.OK, response_model=EletronicoRead
)
async def delete(
    id: int,
    session: AsyncSession = Depends(EngineApp.get_async_session),
    current_user=Depends(Dependencies.get_current_user),
):
    service = EletronicoService(session)
    return await service.delete(id)
