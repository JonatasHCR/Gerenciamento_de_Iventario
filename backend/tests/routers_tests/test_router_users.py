from http import HTTPStatus

import pytest

URL_USUARIO = '/users/'


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_user(async_client, usuario_teste):

    response = await async_client.post(URL_USUARIO, json=usuario_teste)

    usuario_teste['id'] = response.json()['id']
    usuario_teste.pop('senha')

    assert response.status_code == HTTPStatus.CREATED
    assert response.json() == usuario_teste


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_user_duplicate_email(async_client, usuario_teste):

    response = await async_client.post(URL_USUARIO, json=usuario_teste)
    assert response.status_code == HTTPStatus.CREATED

    response = await async_client.post(URL_USUARIO, json=usuario_teste)
    assert response.status_code == HTTPStatus.CONFLICT


@pytest.mark.asyncio
@pytest.mark.routers
async def test_get_users(async_client, usuario_teste):

    await async_client.post(URL_USUARIO, json=usuario_teste)

    response = await async_client.get(URL_USUARIO)

    usuario_teste['id'] = response.json()['users'][0]['id']
    usuario_teste.pop('senha')

    assert response.status_code == HTTPStatus.OK
    assert isinstance(response.json()['users'], list)
    assert response.json()['users'][0] == usuario_teste


@pytest.mark.asyncio
@pytest.mark.routers
async def test_update_user(async_client, usuario_teste):

    response = await async_client.post(URL_USUARIO, json=usuario_teste)
    assert response.status_code == HTTPStatus.CREATED

    usuario_id = response.json()['id']

    updated_usuario = {
        'id': usuario_id,
        'nome': 'João Souza',
        'email': 'joao.souza@example.com',
        'senha': 'nova_senha123',
        'tipo': 'adm',
        'username': 'joao.souza',
    }

    response = await async_client.put(
        f'{URL_USUARIO}{usuario_id}/',
        json=updated_usuario,
        follow_redirects=True,
    )

    updated_usuario.pop('senha')

    assert response.status_code == HTTPStatus.OK
    assert response.json() == updated_usuario


@pytest.mark.asyncio
@pytest.mark.routers
async def test_update_user_not_found(async_client, usuario_teste):

    response = await async_client.post(URL_USUARIO, json=usuario_teste)
    assert response.status_code == HTTPStatus.CREATED

    usuario_id = response.json()['id'] + 1

    updated_usuario = {
        'id': usuario_id,
        'nome': 'João Souza',
        'email': 'joao.souza@example.com',
        'senha': 'nova_senha123',
        'tipo': 'adm',
        'username': 'joao.souza',
    }
    response = await async_client.put(
        f'{URL_USUARIO}{usuario_id}/',
        json=updated_usuario,
        follow_redirects=True,
    )

    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
@pytest.mark.routers
async def test_delete_user(async_client, usuario_teste):

    response = await async_client.post(URL_USUARIO, json=usuario_teste)
    assert response.status_code == HTTPStatus.CREATED

    usuario_id = response.json()['id']

    usuario_teste['id'] = usuario_id
    usuario_teste.pop('senha')

    response = await async_client.delete(
        f'{URL_USUARIO}{usuario_id}/', follow_redirects=True
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == usuario_teste


@pytest.mark.asyncio
@pytest.mark.routers
async def test_delete_user_not_found(async_client, usuario_teste):

    response = await async_client.post(URL_USUARIO, json=usuario_teste)
    assert response.status_code == HTTPStatus.CREATED

    usuario_id = response.json()['id'] + 1

    response = await async_client.delete(
        f'{URL_USUARIO}{usuario_id}/', follow_redirects=True
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
