from http import HTTPStatus

import pytest

URL_ELETRONICO = '/eletronicos/'


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_eletronico(async_client, eletronico_teste, login_teste):

    token_teste = login_teste['token']

    response = await async_client.post(
        URL_ELETRONICO,
        json=eletronico_teste,
        headers={'Authorization': f'Bearer {token_teste}'},
    )
    eletronico_teste['id'] = response.json()['id']

    assert response.status_code == HTTPStatus.CREATED
    assert response.json() == eletronico_teste


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_eletronico_integrity_error(
    async_client, eletronico_teste, login_teste
):

    token_teste = login_teste['token']

    response = await async_client.post(
        URL_ELETRONICO,
        json=eletronico_teste,
        headers={'Authorization': f'Bearer {token_teste}'},
    )
    response = await async_client.post(
        URL_ELETRONICO,
        json=eletronico_teste,
        headers={'Authorization': f'Bearer {token_teste}'},
    )

    assert response.status_code == HTTPStatus.CONFLICT


@pytest.mark.asyncio
@pytest.mark.routers
async def test_get_eletronicos(async_client, eletronico_teste, login_teste):

    token_teste = login_teste['token']

    response = await async_client.post(
        URL_ELETRONICO,
        json=eletronico_teste,
        headers={'Authorization': f'Bearer {token_teste}'},
    )

    response = await async_client.get(
        URL_ELETRONICO, headers={'Authorization': f'Bearer {token_teste}'}
    )

    assert response.status_code == HTTPStatus.OK
    assert isinstance(response.json()['eletronicos'], list)


@pytest.mark.asyncio
@pytest.mark.routers
async def test_update_eletronico(async_client, eletronico_teste, login_teste):

    token_teste = login_teste['token']

    response = await async_client.post(
        URL_ELETRONICO,
        json=eletronico_teste,
        headers={'Authorization': f'Bearer {token_teste}'},
    )
    assert response.status_code == HTTPStatus.CREATED

    eletronico_id = response.json()['id']

    updated_eletronico = {
        'id': eletronico_id,
        'numero_serie': 'SN123456789',
        'numero_patrimonio': 'PT123456789',
        'nome': 'Notebook Lenovo',
        'marca': 'Lenovo',
        'tipo': 'Notbook',
        'modelo': 'ThinkPad X1',
        'status': 'Interno',
        'localizacao': 'Sala de adm',
        'descricao': 'Notebook para uso externo da empresa',
        'ip': '10.0.0.1',
        'centro_custo': '0001',
    }

    response = await async_client.put(
        f'{URL_ELETRONICO}{eletronico_id}',
        json=updated_eletronico,
        headers={'Authorization': f'Bearer {token_teste}'},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == updated_eletronico


@pytest.mark.asyncio
@pytest.mark.routers
async def test_update_eletronico_not_found(
    async_client, eletronico_teste, login_teste
):

    token_teste = login_teste['token']

    response = await async_client.post(
        URL_ELETRONICO,
        json=eletronico_teste,
        headers={'Authorization': f'Bearer {token_teste}'},
    )
    assert response.status_code == HTTPStatus.CREATED

    eletronico_id = response.json()['id'] + 1

    updated_eletronico = {
        'id': eletronico_id,
        'numero_serie': 'SN123456789',
        'numero_patrimonio': 'PT123456789',
        'nome': 'Notebook Lenovo',
        'marca': 'Lenovo',
        'tipo': 'Notbook',
        'modelo': 'ThinkPad X1',
        'status': 'Interno',
        'localizacao': 'Sala de adm',
        'descricao': 'Notebook para uso externo da empresa',
        'ip': '10.0.0.1',
        'centro_custo': '0001',
    }

    response = await async_client.put(
        f'{URL_ELETRONICO}{eletronico_id}',
        json=updated_eletronico,
        headers={'Authorization': f'Bearer {token_teste}'},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
@pytest.mark.routers
async def test_update_eletronico_integrity_error(
    async_client, eletronico_teste, login_teste
):
    token_teste = login_teste['token']

    response = await async_client.post(
        URL_ELETRONICO,
        json=eletronico_teste,
        headers={'Authorization': f'Bearer {token_teste}'},
    )
    assert response.status_code == HTTPStatus.CREATED

    eletronico_id = response.json()['id']

    updated_eletronico = {
        'id': eletronico_id,
        'numero_serie': 'SN123456787',
        'numero_patrimonio': 'PT123456787',
        'nome': 'Notebook Lenovo',
        'marca': 'Lenovo',
        'tipo': 'Notbook',
        'modelo': 'ThinkPad X1',
        'status': 'Interno',
        'localizacao': 'Sala de adm',
        'descricao': 'Notebook para uso externo da empresa',
        'ip': '10.0.0.7',
        'centro_custo': '0001',
    }

    response = await async_client.post(
        URL_ELETRONICO,
        json=updated_eletronico,
        headers={'Authorization': f'Bearer {token_teste}'},
    )
    assert response.status_code == HTTPStatus.CREATED

    response = await async_client.put(
        f'{URL_ELETRONICO}{eletronico_id}',
        json=updated_eletronico,
        headers={'Authorization': f'Bearer {token_teste}'},
    )

    assert response.status_code == HTTPStatus.CONFLICT


@pytest.mark.asyncio
@pytest.mark.routers
async def test_delete_eletronico(async_client, eletronico_teste, login_teste):

    token_teste = login_teste['token']

    response = await async_client.post(
        URL_ELETRONICO,
        json=eletronico_teste,
        headers={'Authorization': f'Bearer {token_teste}'},
    )
    assert response.status_code == HTTPStatus.CREATED

    eletronico_id = response.json()['id']

    eletronico_teste['id'] = eletronico_id
    response = await async_client.delete(
        f'{URL_ELETRONICO}{eletronico_id}',
        headers={'Authorization': f'Bearer {token_teste}'},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == eletronico_teste


@pytest.mark.asyncio
@pytest.mark.routers
async def test_delete_eletronico_not_found(
    async_client, eletronico_teste, login_teste
):
    token_teste = login_teste['token']

    response = await async_client.post(
        URL_ELETRONICO,
        json=eletronico_teste,
        headers={'Authorization': f'Bearer {token_teste}'},
    )
    assert response.status_code == HTTPStatus.CREATED

    eletronico_id = response.json()['id'] + 1

    response = await async_client.delete(
        f'{URL_ELETRONICO}{eletronico_id}',
        headers={'Authorization': f'Bearer {token_teste}'},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
