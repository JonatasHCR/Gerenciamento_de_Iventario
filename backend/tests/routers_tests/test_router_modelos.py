"""Tests do CRUD de modelos (associados a marca)."""

from http import HTTPStatus
from itertools import count

import pytest

from backend.model.contratos import Contrato
from backend.model.eletronicos import Eletronico
from backend.model.user import User
from backend.security.security import Security

URL = '/modelos/'
MARCAS_URL = '/marcas/'
_counter = count(1)


def _n():
    return next(_counter)


async def _criar_usuario(async_db, tipo='Funcionario'):
    n = _n()
    security = Security()
    senha = 'senha12345'
    u = User(
        nome=f'ModeloUser{n}',
        email=f'modelo{n}@t.com',
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


async def _criar_marca(async_client, token, nome):
    resp = await async_client.post(
        MARCAS_URL,
        json={'nome': nome},
        headers={'Authorization': f'Bearer {token}'},
    )
    return resp.json()['id']


# ─── LIST ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_list_modelos_qualquer_autenticado(async_client, async_db):
    func, fsenha = await _criar_usuario(async_db)
    token = await _login(async_client, func.email, fsenha)

    resp = await async_client.get(
        URL, headers={'Authorization': f'Bearer {token}'}
    )

    assert resp.status_code == HTTPStatus.OK
    assert isinstance(resp.json()['modelos'], list)


@pytest.mark.asyncio
@pytest.mark.routers
async def test_list_modelos_filtra_por_marca(async_client, login_teste):
    token = login_teste['token']
    m1 = await _criar_marca(async_client, token, 'MarcaFiltro1')
    m2 = await _criar_marca(async_client, token, 'MarcaFiltro2')
    await async_client.post(
        URL,
        json={'nome': 'Mod1', 'marca_id': m1},
        headers={'Authorization': f'Bearer {token}'},
    )
    await async_client.post(
        URL,
        json={'nome': 'Mod2', 'marca_id': m2},
        headers={'Authorization': f'Bearer {token}'},
    )

    resp = await async_client.get(
        f'{URL}?marca_id={m1}',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert resp.status_code == HTTPStatus.OK
    nomes = {m['nome'] for m in resp.json()['modelos']}
    assert 'Mod1' in nomes
    assert 'Mod2' not in nomes


# ─── CREATE ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_modelo_funcionario(async_client, async_db, login_teste):
    # Admin cria a marca; funcionário cria o modelo (aberto a autenticado)
    marca_id = await _criar_marca(async_client, login_teste['token'], 'Dell')
    func, fsenha = await _criar_usuario(async_db)
    token = await _login(async_client, func.email, fsenha)

    resp = await async_client.post(
        URL,
        json={
            'nome': 'Latitude 5420',
            'marca_id': marca_id,
            'descricao': 'Notebook corporativo',
        },
        headers={'Authorization': f'Bearer {token}'},
    )

    assert resp.status_code == HTTPStatus.CREATED
    body = resp.json()
    assert body['nome'] == 'Latitude 5420'
    assert body['marca_id'] == marca_id
    assert body['marca_nome'] == 'Dell'
    assert body['descricao'] == 'Notebook corporativo'


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_modelo_marca_inexistente(async_client, login_teste):
    resp = await async_client.post(
        URL,
        json={'nome': 'Fantasma', 'marca_id': 99999},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_modelo_duplicado_na_mesma_marca(
    async_client, login_teste
):
    token = login_teste['token']
    marca_id = await _criar_marca(async_client, token, 'HP')
    await async_client.post(
        URL,
        json={'nome': 'EliteBook', 'marca_id': marca_id},
        headers={'Authorization': f'Bearer {token}'},
    )
    resp = await async_client.post(
        URL,
        json={'nome': 'EliteBook', 'marca_id': marca_id},
        headers={'Authorization': f'Bearer {token}'},
    )

    assert resp.status_code == HTTPStatus.CONFLICT


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_modelo_mesmo_nome_marcas_diferentes(
    async_client, login_teste
):
    """O mesmo nome de modelo pode existir em marcas diferentes."""
    token = login_teste['token']
    m1 = await _criar_marca(async_client, token, 'MarcaA')
    m2 = await _criar_marca(async_client, token, 'MarcaB')
    r1 = await async_client.post(
        URL,
        json={'nome': 'Pro 1', 'marca_id': m1},
        headers={'Authorization': f'Bearer {token}'},
    )
    r2 = await async_client.post(
        URL,
        json={'nome': 'Pro 1', 'marca_id': m2},
        headers={'Authorization': f'Bearer {token}'},
    )

    assert r1.status_code == HTTPStatus.CREATED
    assert r2.status_code == HTTPStatus.CREATED


# ─── UPDATE (Admin only) ─────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_update_modelo_admin(async_client, login_teste):
    token = login_teste['token']
    marca_id = await _criar_marca(async_client, token, 'MarcaUpd')
    create = await async_client.post(
        URL,
        json={'nome': 'Modelo Velho', 'marca_id': marca_id},
        headers={'Authorization': f'Bearer {token}'},
    )
    modelo_id = create.json()['id']

    resp = await async_client.put(
        f'{URL}{modelo_id}',
        json={'nome': 'Modelo Novo', 'descricao': 'Atualizado'},
        headers={'Authorization': f'Bearer {token}'},
    )

    assert resp.status_code == HTTPStatus.OK
    assert resp.json()['nome'] == 'Modelo Novo'
    assert resp.json()['descricao'] == 'Atualizado'


@pytest.mark.asyncio
@pytest.mark.routers
async def test_update_modelo_nao_admin_proibido(
    async_client, async_db, login_teste
):
    token = login_teste['token']
    marca_id = await _criar_marca(async_client, token, 'MarcaUpd2')
    create = await async_client.post(
        URL,
        json={'nome': 'Bloqueado', 'marca_id': marca_id},
        headers={'Authorization': f'Bearer {token}'},
    )
    modelo_id = create.json()['id']
    func, fsenha = await _criar_usuario(async_db)
    ftoken = await _login(async_client, func.email, fsenha)

    resp = await async_client.put(
        f'{URL}{modelo_id}',
        json={'nome': 'Hack'},
        headers={'Authorization': f'Bearer {ftoken}'},
    )

    assert resp.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
@pytest.mark.routers
async def test_update_modelo_renomeia_cascata(
    async_client, async_db, login_teste
):
    token = login_teste['token']
    cc = Contrato(centro_custo='MD01', descricao='Modelo Cascade')
    async_db.add(cc)
    await async_db.flush()
    el = Eletronico(
        numero_serie='SN-MD01',
        numero_patrimonio='PAT-MD01',
        nome='Equip',
        tipo='Scanner',
        status='Interno',
        centro_custo='MD01',
        marca='Dell',
        modelo='XPS 13',
    )
    async_db.add(el)
    await async_db.flush()
    await async_db.refresh(el)

    marca_id = await _criar_marca(async_client, token, 'DellCascade')
    create = await async_client.post(
        URL,
        json={'nome': 'XPS 13', 'marca_id': marca_id},
        headers={'Authorization': f'Bearer {token}'},
    )
    modelo_id = create.json()['id']

    resp = await async_client.put(
        f'{URL}{modelo_id}',
        json={'nome': 'XPS 13 Plus'},
        headers={'Authorization': f'Bearer {token}'},
    )
    assert resp.status_code == HTTPStatus.OK

    el_resp = await async_client.get(
        '/eletronicos/',
        headers={'Authorization': f'Bearer {token}'},
    )
    target = next(
        (e for e in el_resp.json()['eletronicos'] if e['id'] == el.id),
        None,
    )
    assert target is not None
    assert target['modelo'] == 'XPS 13 Plus'


@pytest.mark.asyncio
@pytest.mark.routers
async def test_update_modelo_nao_encontrado(async_client, login_teste):
    resp = await async_client.put(
        f'{URL}99999',
        json={'nome': 'Inexistente'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.NOT_FOUND


# ─── DELETE (Admin only) ─────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_delete_modelo_admin(async_client, login_teste):
    token = login_teste['token']
    marca_id = await _criar_marca(async_client, token, 'MarcaDel')
    create = await async_client.post(
        URL,
        json={'nome': 'TempModelo', 'marca_id': marca_id},
        headers={'Authorization': f'Bearer {token}'},
    )
    modelo_id = create.json()['id']

    resp = await async_client.delete(
        f'{URL}{modelo_id}',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert resp.status_code == HTTPStatus.OK


@pytest.mark.asyncio
@pytest.mark.routers
async def test_delete_modelo_nao_admin_proibido(
    async_client, async_db, login_teste
):
    token = login_teste['token']
    marca_id = await _criar_marca(async_client, token, 'MarcaDel2')
    create = await async_client.post(
        URL,
        json={'nome': 'NaoDeletavel', 'marca_id': marca_id},
        headers={'Authorization': f'Bearer {token}'},
    )
    modelo_id = create.json()['id']
    func, fsenha = await _criar_usuario(async_db)
    ftoken = await _login(async_client, func.email, fsenha)

    resp = await async_client.delete(
        f'{URL}{modelo_id}',
        headers={'Authorization': f'Bearer {ftoken}'},
    )

    assert resp.status_code == HTTPStatus.FORBIDDEN
