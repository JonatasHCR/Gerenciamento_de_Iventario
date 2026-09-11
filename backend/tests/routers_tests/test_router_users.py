from http import HTTPStatus

import pytest

URL_USUARIO = '/users/'


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_user_duplicate_email(async_client, login_teste):
    """Criação por Admin em `/users/admin`.

    O antigo `POST /users/` público não existe mais — quem cria identidade é o
    Keycloak. Esta rota continua útil para pré-cadastrar alguém já com o papel
    certo, em vez de esperar o provisionamento (que entra como Funcionario).
    """
    headers = {'Authorization': f'Bearer {login_teste["token"]}'}
    novo = {'nome': 'Duplicado', 'email': 'dup@teste.com', 'tipo': 'Funcionario'}

    response = await async_client.post(
        f'{URL_USUARIO}admin', json=novo, headers=headers
    )
    assert response.status_code == HTTPStatus.CREATED

    response = await async_client.post(
        f'{URL_USUARIO}admin', json=novo, headers=headers
    )
    assert response.status_code == HTTPStatus.CONFLICT


@pytest.mark.asyncio
@pytest.mark.routers
async def test_get_users(async_client, login_teste):

    token_teste = login_teste['token']
    usuario_teste = login_teste['user']

    response = await async_client.get(
        URL_USUARIO, headers={'Authorization': f'Bearer {token_teste}'}
    )

    usuario_teste['id'] = response.json()['users'][0]['id']

    assert response.status_code == HTTPStatus.OK
    assert isinstance(response.json()['users'], list)
    assert response.json()['users'][0] == usuario_teste


@pytest.mark.asyncio
@pytest.mark.routers
async def test_update_user(async_client, login_teste, usuario_teste):

    token_teste = login_teste['token']

    response = await async_client.get(
        URL_USUARIO, headers={'Authorization': f'Bearer {token_teste}'}
    )

    usuario_id = response.json()['users'][0]['id']

    antes = response.json()['users'][0]

    response = await async_client.put(
        f'{URL_USUARIO}{usuario_id}',
        json={'tipo': 'Admin'},
        headers={'Authorization': f'Bearer {token_teste}'},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json()['tipo'] == 'Admin'
    # Nome e email vem do Keycloak: o PUT nao os toca.
    assert response.json()['nome'] == antes['nome']
    assert response.json()['email'] == antes['email']


@pytest.mark.asyncio
@pytest.mark.routers
async def test_update_user_not_found(async_client, login_teste):
    token_teste = login_teste['token']

    response = await async_client.get(
        URL_USUARIO, headers={'Authorization': f'Bearer {token_teste}'}
    )

    usuario_id = response.json()['users'][0]['id'] + 1

    response = await async_client.put(
        f'{URL_USUARIO}{usuario_id}',
        json={'tipo': 'Admin'},
        headers={'Authorization': f'Bearer {token_teste}'},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
@pytest.mark.routers
async def test_update_ignora_nome_e_email(async_client, login_teste):
    """Quem manda neles e o Keycloak; aceitar aqui divergiria para sempre."""
    token_teste = login_teste['token']

    response = await async_client.get(
        URL_USUARIO, headers={'Authorization': f'Bearer {token_teste}'}
    )
    antes = response.json()['users'][0]

    response = await async_client.put(
        f'{URL_USUARIO}{antes["id"]}',
        json={'nome': 'Outro Nome', 'email': 'outro@example.com'},
        headers={'Authorization': f'Bearer {token_teste}'},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json()['nome'] == antes['nome']
    assert response.json()['email'] == antes['email']


@pytest.mark.asyncio
@pytest.mark.routers
async def test_delete_user(async_client, login_teste):

    token_teste = login_teste['token']
    usuario_teste = login_teste['user']

    response = await async_client.get(
        URL_USUARIO, headers={'Authorization': f'Bearer {token_teste}'}
    )

    usuario_id = response.json()['users'][0]['id']

    usuario_teste['id'] = usuario_id

    response = await async_client.delete(
        f'{URL_USUARIO}{usuario_id}',
        headers={'Authorization': f'Bearer {token_teste}'},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == usuario_teste


@pytest.mark.asyncio
@pytest.mark.routers
async def test_delete_user_not_found(async_client, login_teste):
    token_teste = login_teste['token']

    response = await async_client.get(
        URL_USUARIO, headers={'Authorization': f'Bearer {token_teste}'}
    )

    usuario_id = response.json()['users'][0]['id'] + 1

    response = await async_client.delete(
        f'{URL_USUARIO}{usuario_id}',
        headers={'Authorization': f'Bearer {token_teste}'},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
