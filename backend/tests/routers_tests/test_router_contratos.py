from http import HTTPStatus

import pytest

contrato_teste = {
    'centro_custo': '5582',
    'descricao': 'Contrato de manutenção de computadores',
}

URL_CONTRATO = '/contratos/'


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_contrato(async_client):
    response = await async_client.post(URL_CONTRATO, json=contrato_teste)
    assert response.status_code == HTTPStatus.CREATED


@pytest.mark.asyncio
@pytest.mark.routers
async def test_get_contratos(async_client):

    await async_client.post(URL_CONTRATO, json=contrato_teste)

    response = await async_client.get(URL_CONTRATO)
    assert response.status_code == HTTPStatus.OK
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
@pytest.mark.routers
async def test_update_contrato(async_client):

    response = await async_client.post(URL_CONTRATO, json=contrato_teste)
    assert response.status_code == HTTPStatus.CREATED
    contrato_centro_custo = response.json()['centro_custo']

    updated_contrato = {
        'centro_custo': '5582',
        'descricao': 'Contrato',
    }
    response = await async_client.patch(
        f'{URL_CONTRATO}{contrato_centro_custo}/',
        json=updated_contrato,
        follow_redirects=True,
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json()['descricao'] == updated_contrato['descricao']


@pytest.mark.asyncio
@pytest.mark.routers
async def test_update_contrato_not_found(async_client):

    response = await async_client.post(URL_CONTRATO, json=contrato_teste)
    assert response.status_code == HTTPStatus.CREATED
    contrato_centro_custo = '9999'

    updated_contrato = {
        'centro_custo': '5582',
        'descricao': 'Contrato',
    }
    response = await async_client.patch(
        f'{URL_CONTRATO}{contrato_centro_custo}/',
        json=updated_contrato,
        follow_redirects=True,
    )
    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
@pytest.mark.routers
async def test_delete_contrato(async_client):
    response = await async_client.post(URL_CONTRATO, json=contrato_teste)
    assert response.status_code == HTTPStatus.CREATED
    contrato_centro_custo = response.json()['centro_custo']

    response = await async_client.delete(
        f'{URL_CONTRATO}{contrato_centro_custo}/', follow_redirects=True
    )
    assert response.status_code == HTTPStatus.NO_CONTENT


@pytest.mark.asyncio
@pytest.mark.routers
async def test_delete_contrato_not_found(async_client):
    response = await async_client.post(URL_CONTRATO, json=contrato_teste)
    assert response.status_code == HTTPStatus.CREATED
    contrato_centro_custo = '9999'

    response = await async_client.delete(
        f'{URL_CONTRATO}{contrato_centro_custo}/', follow_redirects=True
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
