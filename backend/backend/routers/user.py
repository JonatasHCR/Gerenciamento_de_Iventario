from http import HTTPStatus

from fastapi.routing import APIRouter

router_user = APIRouter(prefix='/users', tags=['users'])


@router_user.get('/', status_code=HTTPStatus.OK)
def get_users():
    return {'message': 'Lista de usuários'}
