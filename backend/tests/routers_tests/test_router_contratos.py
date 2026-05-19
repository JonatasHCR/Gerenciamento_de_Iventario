from http import HTTPStatus

import pytest

URL_CONTRATO = '/contratos/'


def _assert_contrato_eq(json_resp: dict, expected: dict) -> None:
    """Compara só os campos do payload, ignorando enriquecimentos
    (gestor_nome, total_membros) adicionados pela response."""
    for key, value in expected.items():
        assert json_resp.get(key) == value, (
            f'{key}: esperado {value!r}, recebido {json_resp.get(key)!r}'
        )


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_contrato(async_client, contrato_teste, login_teste):

    token = login_teste['token']
    response = await async_client.post(
        URL_CONTRATO,
        json=contrato_teste,
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == HTTPStatus.CREATED
    _assert_contrato_eq(response.json(), contrato_teste)


@pytest.mark.asyncio
@pytest.mark.routers
async def test_get_contratos(async_client, contrato_teste, login_teste):

    token = login_teste['token']
    await async_client.post(
        URL_CONTRATO,
        json=contrato_teste,
        headers={'Authorization': f'Bearer {token}'},
    )

    response = await async_client.get(
        URL_CONTRATO,
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response.status_code == HTTPStatus.OK
    assert isinstance(response.json()['contratos'], list)
    _assert_contrato_eq(response.json()['contratos'][0], contrato_teste)


@pytest.mark.asyncio
@pytest.mark.routers
async def test_update_contrato(async_client, contrato_teste, login_teste):

    token = login_teste['token']
    response = await async_client.post(
        URL_CONTRATO,
        json=contrato_teste,
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response.status_code == HTTPStatus.CREATED

    updated_contrato = {
        'centro_custo': contrato_teste['centro_custo'],
        'descricao': 'Contrato',
    }
    response = await async_client.put(
        f'{URL_CONTRATO}{contrato_teste["centro_custo"]}',
        json=updated_contrato,
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response.status_code == HTTPStatus.OK
    _assert_contrato_eq(response.json(), updated_contrato)


@pytest.mark.asyncio
@pytest.mark.routers
async def test_update_contrato_not_found(
    async_client, contrato_teste, login_teste
):

    token = login_teste['token']
    response = await async_client.post(
        URL_CONTRATO,
        json=contrato_teste,
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response.status_code == HTTPStatus.CREATED
    centro_custo = '9999'

    updated_contrato = {
        'centro_custo': centro_custo,
        'descricao': 'Contrato',
    }
    response = await async_client.put(
        f'{URL_CONTRATO}{centro_custo}',
        json=updated_contrato,
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
@pytest.mark.routers
async def test_delete_contrato(async_client, contrato_teste, login_teste):

    token = login_teste['token']
    response = await async_client.post(
        URL_CONTRATO,
        json=contrato_teste,
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response.status_code == HTTPStatus.CREATED

    response = await async_client.delete(
        f'{URL_CONTRATO}{contrato_teste["centro_custo"]}',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == HTTPStatus.OK
    _assert_contrato_eq(response.json(), contrato_teste)


@pytest.mark.asyncio
@pytest.mark.routers
async def test_delete_contrato_not_found(
    async_client, contrato_teste, login_teste
):

    token = login_teste['token']
    response = await async_client.post(
        URL_CONTRATO,
        json=contrato_teste,
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response.status_code == HTTPStatus.CREATED

    centro_custo = '9999'

    response = await async_client.delete(
        f'{URL_CONTRATO}{centro_custo}',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
