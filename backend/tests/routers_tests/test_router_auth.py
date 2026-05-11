from datetime import datetime
from http import HTTPStatus

import pytest
from freezegun import freeze_time

URL_AUTH = '/auth/'
URL_USUARIO = '/users/'

EXPIRED_TIME_MINUTES = 31


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


@pytest.mark.asyncio
@pytest.mark.routers
async def test_expired_token(async_client, usuario_teste):

    time = datetime(2025, 5, 11, 15, 0, 0).strftime('%Y-%m-%d %H:%M:%S')

    time_expired = datetime(2025, 5, 11, 15, EXPIRED_TIME_MINUTES, 0).strftime(
        '%Y-%m-%d %H:%M:%S'
    )

    with freeze_time(time):
        await async_client.post(f'{URL_USUARIO}', json=usuario_teste)

        form_data = {
            'username': usuario_teste['email'],
            'password': usuario_teste['senha'],
        }
        response = await async_client.post(
            f'{URL_AUTH}login',
            data=form_data,
        )

        token = response.json()['access_token']

        assert response.status_code == HTTPStatus.OK
        assert 'access_token' in response.json()
        assert response.json()['token_type'] == 'Bearer'

    with freeze_time(time_expired):
        response = await async_client.get(
            URL_USUARIO, headers={'Authorization': f'Bearer {token}'}
        )

        assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.asyncio
@pytest.mark.routers
async def test_refresh_token(async_client, login_teste):

    token_teste = login_teste['token']

    response = await async_client.post(
        f'{URL_AUTH}refresh_token',
        headers={'Authorization': f'Bearer {token_teste}'},
    )

    assert response.status_code == HTTPStatus.OK
    assert 'access_token' in response.json()
    assert response.json()['token_type'] == 'Bearer'


@pytest.mark.asyncio
@pytest.mark.routers
async def test_expired_token_dont_refresh(async_client, usuario_teste):

    time = datetime(2025, 5, 11, 15, 0, 0).strftime('%Y-%m-%d %H:%M:%S')

    time_expired = datetime(2025, 5, 11, 15, EXPIRED_TIME_MINUTES, 0).strftime(
        '%Y-%m-%d %H:%M:%S'
    )

    with freeze_time(time):
        await async_client.post(f'{URL_USUARIO}', json=usuario_teste)

        form_data = {
            'username': usuario_teste['email'],
            'password': usuario_teste['senha'],
        }
        response = await async_client.post(
            f'{URL_AUTH}login',
            data=form_data,
        )

        token = response.json()['access_token']

        assert response.status_code == HTTPStatus.OK
        assert 'access_token' in response.json()
        assert response.json()['token_type'] == 'Bearer'

    with freeze_time(time_expired):
        response = await async_client.post(
            f'{URL_AUTH}refresh_token',
            headers={'Authorization': f'Bearer {token}'},
        )

        assert response.status_code == HTTPStatus.UNAUTHORIZED
