from http import HTTPStatus

import pytest

URL_AUTH = '/auth/'
URL_USUARIO = '/users/'


@pytest.mark.asyncio
@pytest.mark.routers
async def test_login(async_client, usuario_teste):

    await async_client.post(f'{URL_USUARIO}', json=usuario_teste)

    form_data = {
        'username': usuario_teste['email'],
        'password': usuario_teste['senha'],
    }
    response = await async_client.post(
        f'{URL_AUTH}login',
        data=form_data,
    )

    assert response.status_code == HTTPStatus.OK
    assert 'access_token' in response.json()
    assert response.json()['token_type'] == 'Bearer'


@pytest.mark.asyncio
@pytest.mark.routers
async def test_login_invalid_credentials_senha(async_client, usuario_teste):

    await async_client.post(f'{URL_USUARIO}', json=usuario_teste)

    form_data = {
        'username': usuario_teste['email'],
        'password': 'senha_incorreta',
    }
    response = await async_client.post(
        f'{URL_AUTH}login',
        data=form_data,
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.asyncio
@pytest.mark.routers
async def test_login_invalid_credentials_email(async_client, usuario_teste):

    await async_client.post(f'{URL_USUARIO}', json=usuario_teste)

    form_data = {
        'username': 'email_incorreto@example.com',
        'password': usuario_teste['senha'],
    }
    response = await async_client.post(
        f'{URL_AUTH}login',
        data=form_data,
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED
