"""Tests do CRUD de marcas."""

from http import HTTPStatus
from itertools import count

import pytest

from backend.model.contratos import Contrato
from backend.model.eletronicos import Eletronico
from backend.model.user import User
from backend.security.security import Security

URL = '/marcas/'
_counter = count(1)


def _n():
    return next(_counter)


async def _criar_usuario(async_db, tipo='Funcionario'):
    n = _n()
    security = Security()
    senha = 'senha12345'
    u = User(
        nome=f'MarcaUser{n}',
        email=f'marca{n}@t.com',
        senha=security.get_senha_hash(senha),
        tipo=tipo,
    )
    async_db.add(u)
    await async_db.flush()
    await async_db.refresh(u)
    return u, senha


async def _login(async_client, email, senha):
    resp = await async_client.post(
        '/auth/login',
        data={'username': email, 'password': senha},
    )
    return resp.json()['access_token']


# ─── LIST ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_list_marcas_qualquer_autenticado(async_client, async_db):
    func, fsenha = await _criar_usuario(async_db)
    token = await _login(async_client, func.email, fsenha)

    resp = await async_client.get(
        URL, headers={'Authorization': f'Bearer {token}'}
    )

    assert resp.status_code == HTTPStatus.OK
    assert isinstance(resp.json()['marcas'], list)


@pytest.mark.asyncio
@pytest.mark.routers
async def test_list_marcas_nao_autenticado_proibido(async_client):
    resp = await async_client.get(URL)
    assert resp.status_code == HTTPStatus.UNAUTHORIZED


# ─── CREATE (aberto a qualquer autenticado) ─────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_marca_funcionario(async_client, async_db):
    func, fsenha = await _criar_usuario(async_db)
    token = await _login(async_client, func.email, fsenha)

    resp = await async_client.post(
        URL,
        json={'nome': 'Dell'},
        headers={'Authorization': f'Bearer {token}'},
    )

    assert resp.status_code == HTTPStatus.CREATED
    body = resp.json()
    assert body['nome'] == 'Dell'
    assert 'descricao' not in body


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_marca_duplicada(async_client, login_teste):
    await async_client.post(
        URL,
        json={'nome': 'HP'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    resp = await async_client.post(
        URL,
        json={'nome': 'HP'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.CONFLICT


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_marca_normaliza_espacos(async_client, login_teste):
    resp = await async_client.post(
        URL,
        json={'nome': '   Lenovo   '},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    assert resp.status_code == HTTPStatus.CREATED
    assert resp.json()['nome'] == 'Lenovo'


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_marca_nome_vazio_proibido(async_client, login_teste):
    resp = await async_client.post(
        URL,
        json={'nome': ''},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


# ─── UPDATE (Admin only) ─────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_update_marca_admin(async_client, login_teste):
    create = await async_client.post(
        URL,
        json={'nome': 'Marca Velha'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    marca_id = create.json()['id']

    resp = await async_client.put(
        f'{URL}{marca_id}',
        json={'nome': 'Marca Nova'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.OK
    assert resp.json()['nome'] == 'Marca Nova'


@pytest.mark.asyncio
@pytest.mark.routers
async def test_update_marca_nao_admin_proibido(
    async_client, async_db, login_teste
):
    create = await async_client.post(
        URL,
        json={'nome': 'Bloqueada'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    marca_id = create.json()['id']
    func, fsenha = await _criar_usuario(async_db)
    token = await _login(async_client, func.email, fsenha)

    resp = await async_client.put(
        f'{URL}{marca_id}',
        json={'nome': 'Hack'},
        headers={'Authorization': f'Bearer {token}'},
    )

    assert resp.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
@pytest.mark.routers
async def test_update_marca_renomeia_cascata(
    async_client, async_db, login_teste
):
    """Renomear a marca atualiza em cascata o campo `marca` dos
    eletrônicos."""
    cc = Contrato(centro_custo='MC01', descricao='Marca Cascade')
    async_db.add(cc)
    await async_db.flush()
    el = Eletronico(
        numero_serie='SN-MC01',
        numero_patrimonio='PAT-MC01',
        nome='Equip',
        tipo='Scanner',
        status='Interno',
        centro_custo='MC01',
        marca='Acer',
    )
    async_db.add(el)
    await async_db.flush()
    await async_db.refresh(el)

    create = await async_client.post(
        URL,
        json={'nome': 'Acer'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    marca_id = create.json()['id']

    resp = await async_client.put(
        f'{URL}{marca_id}',
        json={'nome': 'Acer Inc'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    assert resp.status_code == HTTPStatus.OK

    el_resp = await async_client.get(
        '/eletronicos/',
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    target = next(
        (e for e in el_resp.json()['eletronicos'] if e['id'] == el.id),
        None,
    )
    assert target is not None
    assert target['marca'] == 'Acer Inc'


@pytest.mark.asyncio
@pytest.mark.routers
async def test_update_marca_nao_encontrada(async_client, login_teste):
    resp = await async_client.put(
        f'{URL}99999',
        json={'nome': 'Inexistente'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.NOT_FOUND


# ─── DELETE (Admin only) ─────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_delete_marca_admin(async_client, login_teste):
    create = await async_client.post(
        URL,
        json={'nome': 'TempMarca'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    marca_id = create.json()['id']

    resp = await async_client.delete(
        f'{URL}{marca_id}',
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    assert resp.status_code == HTTPStatus.OK

    list_resp = await async_client.get(
        URL, headers={'Authorization': f'Bearer {login_teste["token"]}'}
    )
    nomes = {m['nome'] for m in list_resp.json()['marcas']}
    assert 'TempMarca' not in nomes


@pytest.mark.asyncio
@pytest.mark.routers
async def test_delete_marca_nao_admin_proibido(
    async_client, async_db, login_teste
):
    create = await async_client.post(
        URL,
        json={'nome': 'NaoDeletavel'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    marca_id = create.json()['id']
    func, fsenha = await _criar_usuario(async_db)
    token = await _login(async_client, func.email, fsenha)

    resp = await async_client.delete(
        f'{URL}{marca_id}',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert resp.status_code == HTTPStatus.FORBIDDEN
