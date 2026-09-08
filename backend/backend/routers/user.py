from http import HTTPStatus
from typing import Annotated

from fastapi import Depends
from fastapi.routing import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.engine import EngineApp
from backend.schemas.user import UserCreate, UserList, UserRead, UserUpdate
from backend.security.dependencies import Dependencies, UserContext
from backend.service.user import UserService

router_user = APIRouter(prefix='/users', tags=['users'])

T_AsyncSession = Annotated[AsyncSession, Depends(EngineApp.get_async_session)]
T_UserContext = Annotated[UserContext, Depends(Dependencies.get_user_context)]


@router_user.get('/me', status_code=HTTPStatus.OK, response_model=UserRead)
async def get_me(ctx: T_UserContext):
    """O usuário autenticado.

    Declarado ANTES de qualquer rota com path param, senão `/me` seria capturado
    como um `{user_id}`.

    Existe porque o frontend precisava saber quem está logado e não tinha como:
    ele decodificava o token e procurava o próprio email na lista completa de
    usuários, repetindo isso a cada 10 segundos. Com o token fora do navegador
    (padrão BFF) aquilo deixou de ser possível — e era caro de qualquer forma.
    """
    return ctx.user


@router_user.get('/', status_code=HTTPStatus.OK, response_model=UserList)
async def get_users(
    session: T_AsyncSession,
    ctx: T_UserContext,
):
    service = UserService(session)
    users = await service.get_users(ctx)
    return {'users': users}


# O `POST /users/` de auto-registro público foi REMOVIDO junto com o SSO: era
# cadastro aberto, sem autenticação, para qualquer um na rede. Quem cria conta
# agora é o Keycloak, e a linha local nasce sozinha no primeiro login válido.


@router_user.post(
    '/admin',
    status_code=HTTPStatus.CREATED,
    response_model=UserRead,
)
async def create_admin(
    user: UserCreate,
    session: T_AsyncSession,
    ctx: T_UserContext,
):
    """Criação de usuário com tipo específico, por um Admin.

    Continua útil para pré-cadastrar alguém já com o papel certo, em vez de
    esperar o provisionamento automático (que entra sempre como Funcionario).
    """
    service = UserService(session)
    return await service.create_admin(user, ctx)


@router_user.put(
    '/{user_id}', status_code=HTTPStatus.OK, response_model=UserRead
)
async def update(
    user_id: int,
    user: UserUpdate,
    session: T_AsyncSession,
    ctx: T_UserContext,
):
    service = UserService(session)
    return await service.update(user_id, user, ctx)


@router_user.delete(
    '/{user_id}', status_code=HTTPStatus.OK, response_model=UserRead
)
async def delete(
    user_id: int,
    session: T_AsyncSession,
    ctx: T_UserContext,
):
    service = UserService(session)
    return await service.delete(user_id, ctx)
