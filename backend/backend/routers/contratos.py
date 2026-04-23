from http import HTTPStatus

from fastapi.routing import APIRouter

router_contratos = APIRouter(prefix='/contratos', tags=['contratos'])


@router_contratos.get('/', status_code=HTTPStatus.OK)
def get_contratos():
    return {'message': 'Lista de contratos'}
