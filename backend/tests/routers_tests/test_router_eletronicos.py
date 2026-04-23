from http import HTTPStatus

import pytest

eletronico_teste = {
    'id': 'E001',
    'numero_serie': 'SN123456789',
    'numero_patrimonio': 'PT123456789',
    'nome': 'Notebook Dell',
    'marca': 'Dell',
    'tipo': 'Notebook',
    'modelo': 'XPS 15',
    'status': 'Interno',
    'ip': '10.0.0.0',
    'centro_custo': '0001',
}

URL_ELETRONICO = '/eletronicos/'


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_eletronico(async_client):
    response = await async_client.post(URL_ELETRONICO, json=eletronico_teste)
    assert response.status_code == HTTPStatus.CREATED


@pytest.mark.asyncio
@pytest.mark.routers
async def test_get_eletronicos(async_client):

    await async_client.post(URL_ELETRONICO, json=eletronico_teste)

    response = await async_client.get(URL_ELETRONICO)
    assert response.status_code == HTTPStatus.OK
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
@pytest.mark.routers
async def test_update_eletronico(async_client):

    response = await async_client.post(URL_ELETRONICO, json=eletronico_teste)
    assert response.status_code == HTTPStatus.CREATED
    eletronico_id = response.json()['id']

    updated_eletronico = {
        'id': 'E001',
        'numero_serie': 'SN123456789',
        'numero_patrimonio': 'PT123456789',
        'nome': 'Notebook Lenovo',
        'marca': 'Lenovo',
        'tipo': 'Notebook',
        'modelo': 'ThinkPad X1',
        'status': 'Interno',
        'ip': '10.0.0.1',
        'centro_custo': '0001',
    }
    response = await async_client.patch(
        f'{URL_ELETRONICO}{eletronico_id}/',
        json=updated_eletronico,
        follow_redirects=True,
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json()['nome'] == updated_eletronico['nome']
    assert response.json()['marca'] == updated_eletronico['marca']
    assert response.json()['modelo'] == updated_eletronico['modelo']
    assert response.json()['ip'] == updated_eletronico['ip']


@pytest.mark.asyncio
@pytest.mark.routers
async def test_update_eletronico_not_found(async_client):

    response = await async_client.post(URL_ELETRONICO, json=eletronico_teste)
    assert response.status_code == HTTPStatus.CREATED
    eletronico_id = response.json()['id'] + 1

    updated_eletronico = {
        'id': 'E001',
        'numero_serie': 'SN123456789',
        'numero_patrimonio': 'PT123456789',
        'nome': 'Notebook Lenovo',
        'marca': 'Lenovo',
        'tipo': 'Notebook',
        'modelo': 'ThinkPad X1',
        'status': 'Interno',
        'ip': '10.0.0.1',
        'centro_custo': '0001',
    }
    response = await async_client.patch(
        f'{URL_ELETRONICO}{eletronico_id}/',
        json=updated_eletronico,
        follow_redirects=True,
    )
    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
@pytest.mark.routers
async def test_delete_eletronico(async_client):
    response = await async_client.post(URL_ELETRONICO, json=eletronico_teste)
    assert response.status_code == HTTPStatus.CREATED
    eletronico_id = response.json()['id']

    response = await async_client.delete(
        f'{URL_ELETRONICO}{eletronico_id}/', follow_redirects=True
    )
    assert response.status_code == HTTPStatus.NO_CONTENT


@pytest.mark.asyncio
@pytest.mark.routers
async def test_delete_eletronico_not_found(async_client):
    response = await async_client.post(URL_ELETRONICO, json=eletronico_teste)
    assert response.status_code == HTTPStatus.CREATED
    eletronico_id = response.json()['id'] + 1

    response = await async_client.delete(
        f'{URL_ELETRONICO}{eletronico_id}/', follow_redirects=True
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
