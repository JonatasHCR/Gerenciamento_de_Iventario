from http import HTTPStatus

from fastapi import Depends
from fastapi.routing import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.engine import EngineApp
from backend.schemas.contratos import (
    ContratoCreate,
    ContratoList,
    ContratoRead,
)
from backend.service.contratos import ContratoService

router_contratos = APIRouter(prefix='/contratos', tags=['contratos'])


@router_contratos.get(
    '/', status_code=HTTPStatus.OK, response_model=ContratoList
)
async def get(session: AsyncSession = Depends(EngineApp.get_async_session)):
    service = ContratoService(session)
    contratos = await service.get()
    return {'contratos': contratos}


@router_contratos.post(
    '/', status_code=HTTPStatus.CREATED, response_model=ContratoRead
)
async def create(
    contrato: ContratoCreate,
    session: AsyncSession = Depends(EngineApp.get_async_session),
):
    service = ContratoService(session)
    return await service.create(contrato)


@router_contratos.put(
    '/{centro_custo}',
    status_code=HTTPStatus.OK,
    response_model=ContratoRead,
)
async def update(
    centro_custo: str,
    contrato: ContratoCreate,
    session: AsyncSession = Depends(EngineApp.get_async_session),
):
    service = ContratoService(session)
    return await service.update(centro_custo, contrato)


@router_contratos.delete(
    '/{centro_custo}', status_code=HTTPStatus.OK, response_model=ContratoRead
)
async def delete(
    centro_custo: str,
    session: AsyncSession = Depends(EngineApp.get_async_session),
):
    service = ContratoService(session)
    return await service.delete(centro_custo)
