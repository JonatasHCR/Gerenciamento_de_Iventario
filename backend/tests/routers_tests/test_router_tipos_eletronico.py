"""Tests do CRUD de tipos de equipamento."""

from http import HTTPStatus
from itertools import count

import pytest

from backend.model.contratos import Contrato
from backend.model.eletronicos import Eletronico
from backend.model.user import User
from backend.security.security import Security

URL = '/tipos-eletronico/'
_counter = count(1)


def _n():
    return next(_counter)


async def _criar_usuario(async_db, tipo='Funcionario'):
    n = _n()
    security = Security()
    senha = 'senha12345'
    u = User(
        nome=f'TipoUser{n}',
        email=f'tipo{n}@t.com',
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
async def test_list_tipos_qualquer_autenticado(
    async_client, async_db
):
    func, fsenha = await _criar_usuario(async_db)
    token = await _login(async_client, func.email, fsenha)

    resp = await async_client.get(
        URL, headers={'Authorization': f'Bearer {token}'}
    )

    assert resp.status_code == HTTPStatus.OK
    tipos = resp.json()['tipos']
    nomes = {t['nome'] for t in tipos}
    # Os 5 do seed inicial
    esperados = {
        'Computador', 'Notbook', 'Monitor', 'Impressora', 'Scanner'
    }
    assert esperados <= nomes


@pytest.mark.asyncio
@pytest.mark.routers
async def test_list_apenas_ativos(async_client, login_teste):
    # cria um inativo
    create = await async_client.post(
        URL,
        json={'nome': 'TipoInativo'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    tipo_id = create.json()['id']
    await async_client.put(
        f'{URL}{tipo_id}',
        json={'ativo': False},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    resp = await async_client.get(
        f'{URL}?apenas_ativos=true',
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    nomes = {t['nome'] for t in resp.json()['tipos']}
    assert 'TipoInativo' not in nomes


# ─── CREATE ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_tipo_admin(async_client, login_teste):
    resp = await async_client.post(
        URL,
        json={'nome': 'Tablet', 'descricao': 'Tablet Android'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.CREATED
    body = resp.json()
    assert body['nome'] == 'Tablet'
    assert body['ativo'] is True


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_tipo_nao_admin_proibido(async_client, async_db):
    gestor, gsenha = await _criar_usuario(async_db, 'Gestor')
    token = await _login(async_client, gestor.email, gsenha)

    resp = await async_client.post(
        URL,
        json={'nome': 'Tablet'},
        headers={'Authorization': f'Bearer {token}'},
    )

    assert resp.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_tipo_duplicado(async_client, login_teste):
    resp = await async_client.post(
        URL,
        json={'nome': 'Computador'},  # já existe no seed
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.CONFLICT


# ─── UPDATE ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_update_tipo_renomeia_cascata(
    async_client, async_db, login_teste
):
    """Renomear o tipo atualiza em cascata o campo `tipo` dos eletrônicos."""
    # Cria contrato + eletrônico do tipo 'Scanner'
    cc = Contrato(centro_custo='UT01', descricao='Tipos Update')
    async_db.add(cc)
    await async_db.flush()
    el = Eletronico(
        numero_serie='SN-UT01',
        numero_patrimonio='PAT-UT01',
        nome='Equip',
        tipo='Scanner',
        status='Interno',
        centro_custo='UT01',
    )
    async_db.add(el)
    await async_db.flush()
    await async_db.refresh(el)

    list_resp = await async_client.get(
        URL, headers={'Authorization': f'Bearer {login_teste["token"]}'}
    )
    scanner_id = next(
        t['id'] for t in list_resp.json()['tipos'] if t['nome'] == 'Scanner'
    )

    resp = await async_client.put(
        f'{URL}{scanner_id}',
        json={'nome': 'Scanner 3D'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    assert resp.status_code == HTTPStatus.OK

    # Verifica que o eletrônico foi atualizado
    eletronicos_resp = await async_client.get(
        '/eletronicos/',
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    nomes_de_tipos = {
        e['tipo'] for e in eletronicos_resp.json()['eletronicos']
    }
    assert 'Scanner 3D' in nomes_de_tipos
    assert 'Scanner' not in nomes_de_tipos


@pytest.mark.asyncio
@pytest.mark.routers
async def test_update_tipo_nao_admin_proibido(async_client, async_db):
    func, fsenha = await _criar_usuario(async_db)
    token = await _login(async_client, func.email, fsenha)

    resp = await async_client.put(
        f'{URL}1',
        json={'nome': 'Hack'},
        headers={'Authorization': f'Bearer {token}'},
    )

    assert resp.status_code == HTTPStatus.FORBIDDEN


# ─── DELETE ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_delete_tipo_sem_uso_remove(async_client, login_teste):
    # cria um tipo novo (sem nenhum equipamento usando)
    create = await async_client.post(
        URL,
        json={'nome': 'TipoTemp'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    tipo_id = create.json()['id']

    resp = await async_client.delete(
        f'{URL}{tipo_id}',
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    assert resp.status_code == HTTPStatus.OK

    list_resp = await async_client.get(
        URL, headers={'Authorization': f'Bearer {login_teste["token"]}'}
    )
    nomes = {t['nome'] for t in list_resp.json()['tipos']}
    assert 'TipoTemp' not in nomes


@pytest.mark.asyncio
@pytest.mark.routers
async def test_delete_tipo_em_uso_apenas_desativa(
    async_client, async_db, login_teste
):
    cc = Contrato(centro_custo='DT01', descricao='Delete tipo')
    async_db.add(cc)
    await async_db.flush()
    async_db.add(
        Eletronico(
            numero_serie='SN-DT01',
            numero_patrimonio='PAT-DT01',
            nome='Equip',
            tipo='Monitor',
            status='Interno',
            centro_custo='DT01',
        )
    )
    await async_db.flush()

    list_resp = await async_client.get(
        URL, headers={'Authorization': f'Bearer {login_teste["token"]}'}
    )
    monitor_id = next(
        t['id'] for t in list_resp.json()['tipos'] if t['nome'] == 'Monitor'
    )

    resp = await async_client.delete(
        f'{URL}{monitor_id}',
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    assert resp.status_code == HTTPStatus.OK
    assert resp.json()['ativo'] is False

    # ainda aparece na listagem (mas como inativo)
    list2 = await async_client.get(
        URL, headers={'Authorization': f'Bearer {login_teste["token"]}'}
    )
    monitor = next(
        t for t in list2.json()['tipos'] if t['nome'] == 'Monitor'
    )
    assert monitor['ativo'] is False


# ─── Validação em eletrônicos ────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_eletronico_tipo_inexistente(
    async_client, async_db, login_teste
):
    cc = Contrato(centro_custo='VAL1', descricao='Validação tipo')
    async_db.add(cc)
    await async_db.flush()

    resp = await async_client.post(
        '/eletronicos/',
        json={
            'numero_serie': 'SN-VAL1',
            'numero_patrimonio': 'PAT-VAL1',
            'nome': 'X',
            'tipo': 'TipoQueNaoExiste',
            'status': 'Interno',
            'centro_custo': 'VAL1',
        },
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_eletronico_tipo_desativado(
    async_client, async_db, login_teste
):
    cc = Contrato(centro_custo='VAL2', descricao='Validação inativo')
    async_db.add(cc)
    await async_db.flush()

    # cria um tipo e desativa
    create = await async_client.post(
        URL,
        json={'nome': 'Plotter'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    tipo_id = create.json()['id']
    await async_client.put(
        f'{URL}{tipo_id}',
        json={'ativo': False},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    resp = await async_client.post(
        '/eletronicos/',
        json={
            'numero_serie': 'SN-VAL2',
            'numero_patrimonio': 'PAT-VAL2',
            'nome': 'X',
            'tipo': 'Plotter',
            'status': 'Interno',
            'centro_custo': 'VAL2',
        },
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
