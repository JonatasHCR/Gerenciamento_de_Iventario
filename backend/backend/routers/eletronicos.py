from http import HTTPStatus

from fastapi.routing import APIRouter

router_eletronicos = APIRouter(prefix='/eletronicos', tags=['eletronicos'])


@router_eletronicos.get('/', status_code=HTTPStatus.OK)
def get_eletronicos():
    return {'message': 'Lista de eletrônicos'}
