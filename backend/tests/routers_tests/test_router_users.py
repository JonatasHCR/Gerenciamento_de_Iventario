from http import HTTPStatus

import pytest

usuario_teste = {
    'nome': 'João Silva',
    'email': 'joao.silva@example.com',
    'senha': 'senha123',
    'tipo': 'funcionario',
}

URL_USUARIO = '/users/'


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_user(async_client):
    response = await async_client.post(URL_USUARIO, json=usuario_teste)
    assert response.status_code == HTTPStatus.CREATED


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_user_duplicate_email(async_client):

    response = await async_client.post(URL_USUARIO, json=usuario_teste)
    assert response.status_code == HTTPStatus.CREATED

    response = await async_client.post(URL_USUARIO, json=usuario_teste)
    assert response.status_code == HTTPStatus.CONFLICT


@pytest.mark.asyncio
@pytest.mark.routers
async def test_get_users(async_client):

    await async_client.post(URL_USUARIO, json=usuario_teste)

    response = await async_client.get(URL_USUARIO)
    assert response.status_code == HTTPStatus.OK
    assert isinstance(response.json()['users'], list)


@pytest.mark.asyncio
@pytest.mark.routers
async def test_update_user(async_client):

    response = await async_client.post(URL_USUARIO, json=usuario_teste)
    assert response.status_code == HTTPStatus.CREATED
    usuario_id = response.json()['id']

    updated_usuario = {
        'nome': 'João Souza',
        'email': 'joao.souza@example.com',
        'senha': 'nova_senha123',
        'tipo': 'adm',
    }
    response = await async_client.put(
        f'{URL_USUARIO}{usuario_id}/',
        json=updated_usuario,
        follow_redirects=True,
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json()['nome'] == updated_usuario['nome']
    assert response.json()['tipo'] == updated_usuario['tipo']


@pytest.mark.asyncio
@pytest.mark.routers
async def test_update_user_not_found(async_client):

    response = await async_client.post(URL_USUARIO, json=usuario_teste)
    assert response.status_code == HTTPStatus.CREATED
    usuario_id = response.json()['id'] + 1

    updated_usuario = {
        'nome': 'João Souza',
        'email': 'joao.souza@example.com',
        'senha': 'nova_senha123',
        'tipo': 'adm',
    }
    response = await async_client.put(
        f'{URL_USUARIO}{usuario_id}/',
        json=updated_usuario,
        follow_redirects=True,
    )
    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
@pytest.mark.routers
async def test_delete_user(async_client):
    response = await async_client.post(URL_USUARIO, json=usuario_teste)
    assert response.status_code == HTTPStatus.CREATED
    usuario_id = response.json()['id']

    response = await async_client.delete(
        f'{URL_USUARIO}{usuario_id}/', follow_redirects=True
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json()['id'] == usuario_id


@pytest.mark.asyncio
@pytest.mark.routers
async def test_delete_user_not_found(async_client):
    response = await async_client.post(URL_USUARIO, json=usuario_teste)
    assert response.status_code == HTTPStatus.CREATED
    usuario_id = response.json()['id'] + 1

    response = await async_client.delete(
        f'{URL_USUARIO}{usuario_id}/', follow_redirects=True
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
