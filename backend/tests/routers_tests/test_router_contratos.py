from http import HTTPStatus

import pytest

URL_CONTRATO = '/contratos/'


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_contrato(async_client, contrato_teste):

    response = await async_client.post(URL_CONTRATO, json=contrato_teste)

    assert response.status_code == HTTPStatus.CREATED
    assert response.json() == contrato_teste


@pytest.mark.asyncio
@pytest.mark.routers
async def test_get_contratos(async_client, contrato_teste):

    await async_client.post(URL_CONTRATO, json=contrato_teste)

    response = await async_client.get(URL_CONTRATO)
    assert response.status_code == HTTPStatus.OK
    assert isinstance(response.json()['contratos'], list)
    assert response.json()['contratos'][0] == contrato_teste


@pytest.mark.asyncio
@pytest.mark.routers
async def test_update_contrato(async_client, contrato_teste):

    response = await async_client.post(URL_CONTRATO, json=contrato_teste)
    assert response.status_code == HTTPStatus.CREATED

    updated_contrato = {
        'centro_custo': contrato_teste['centro_custo'],
        'descricao': 'Contrato',
    }
    response = await async_client.put(
        f'{URL_CONTRATO}{contrato_teste["centro_custo"]}',
        json=updated_contrato,
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json() == updated_contrato


@pytest.mark.asyncio
@pytest.mark.routers
async def test_update_contrato_not_found(async_client, contrato_teste):

    response = await async_client.post(URL_CONTRATO, json=contrato_teste)
    assert response.status_code == HTTPStatus.CREATED
    centro_custo = '9999'

    updated_contrato = {
        'centro_custo': centro_custo,
        'descricao': 'Contrato',
    }
    response = await async_client.put(
        f'{URL_CONTRATO}{centro_custo}',
        json=updated_contrato,
    )
    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
@pytest.mark.routers
async def test_delete_contrato(async_client, contrato_teste):

    response = await async_client.post(URL_CONTRATO, json=contrato_teste)
    assert response.status_code == HTTPStatus.CREATED

    response = await async_client.delete(
        f'{URL_CONTRATO}{contrato_teste["centro_custo"]}',
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == contrato_teste


@pytest.mark.asyncio
@pytest.mark.routers
async def test_delete_contrato_not_found(async_client, contrato_teste):

    response = await async_client.post(URL_CONTRATO, json=contrato_teste)
    assert response.status_code == HTTPStatus.CREATED

    centro_custo = '9999'

    response = await async_client.delete(
        f'{URL_CONTRATO}{centro_custo}',
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
