"""Tests do CRUD de localizações."""

from http import HTTPStatus
from itertools import count

import pytest

from backend.model.contratos import Contrato
from backend.model.eletronicos import Eletronico
from backend.model.user import User
from backend.security.security import Security

URL = '/localizacoes/'
_counter = count(1)


def _n():
    return next(_counter)


async def _criar_usuario(async_db, tipo='Funcionario'):
    n = _n()
    security = Security()
    senha = 'senha12345'
    u = User(
        nome=f'LocUser{n}',
        email=f'loc{n}@t.com',
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
async def test_list_localizacoes_qualquer_autenticado(
    async_client, async_db
):
    func, fsenha = await _criar_usuario(async_db)
    token = await _login(async_client, func.email, fsenha)

    resp = await async_client.get(
        URL, headers={'Authorization': f'Bearer {token}'}
    )

    assert resp.status_code == HTTPStatus.OK
    assert isinstance(resp.json()['localizacoes'], list)


@pytest.mark.asyncio
@pytest.mark.routers
async def test_list_localizacoes_nao_autenticado_proibido(async_client):
    resp = await async_client.get(URL)
    assert resp.status_code == HTTPStatus.UNAUTHORIZED


# ─── CREATE (aberto a qualquer autenticado) ─────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_localizacao_funcionario(async_client, async_db):
    """Funcionário (qualquer autenticado) pode criar."""
    func, fsenha = await _criar_usuario(async_db)
    token = await _login(async_client, func.email, fsenha)

    resp = await async_client.post(
        URL,
        json={'nome': 'Sala TI', 'descricao': 'Sala da equipe de TI'},
        headers={'Authorization': f'Bearer {token}'},
    )

    assert resp.status_code == HTTPStatus.CREATED
    body = resp.json()
    assert body['nome'] == 'Sala TI'
    assert body['descricao'] == 'Sala da equipe de TI'


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_localizacao_admin(async_client, login_teste):
    resp = await async_client.post(
        URL,
        json={'nome': 'Almoxarifado'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.CREATED
    assert resp.json()['nome'] == 'Almoxarifado'


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_localizacao_duplicada(async_client, login_teste):
    await async_client.post(
        URL,
        json={'nome': 'Recepção'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    resp = await async_client.post(
        URL,
        json={'nome': 'Recepção'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.CONFLICT


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_localizacao_normaliza_espacos(
    async_client, login_teste
):
    resp = await async_client.post(
        URL,
        json={'nome': '   Sala Diretoria   '},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    assert resp.status_code == HTTPStatus.CREATED
    assert resp.json()['nome'] == 'Sala Diretoria'


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_localizacao_nome_vazio_proibido(
    async_client, login_teste
):
    resp = await async_client.post(
        URL,
        json={'nome': ''},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


# ─── UPDATE (Admin only) ─────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_update_localizacao_admin(async_client, login_teste):
    create = await async_client.post(
        URL,
        json={'nome': 'Loc Velha'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    loc_id = create.json()['id']

    resp = await async_client.put(
        f'{URL}{loc_id}',
        json={'nome': 'Loc Nova', 'descricao': 'Atualizada'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.OK
    assert resp.json()['nome'] == 'Loc Nova'
    assert resp.json()['descricao'] == 'Atualizada'


@pytest.mark.asyncio
@pytest.mark.routers
async def test_update_localizacao_nao_admin_proibido(
    async_client, async_db, login_teste
):
    create = await async_client.post(
        URL,
        json={'nome': 'Bloqueada'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    loc_id = create.json()['id']
    func, fsenha = await _criar_usuario(async_db)
    token = await _login(async_client, func.email, fsenha)

    resp = await async_client.put(
        f'{URL}{loc_id}',
        json={'nome': 'Hack'},
        headers={'Authorization': f'Bearer {token}'},
    )

    assert resp.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
@pytest.mark.routers
async def test_update_localizacao_gestor_proibido(
    async_client, async_db, login_teste
):
    create = await async_client.post(
        URL,
        json={'nome': 'GestorBloqueado'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    loc_id = create.json()['id']
    gestor, gsenha = await _criar_usuario(async_db, 'Gestor')
    token = await _login(async_client, gestor.email, gsenha)

    resp = await async_client.put(
        f'{URL}{loc_id}',
        json={'nome': 'TentativaGestor'},
        headers={'Authorization': f'Bearer {token}'},
    )

    assert resp.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
@pytest.mark.routers
async def test_update_localizacao_renomeia_cascata(
    async_client, async_db, login_teste
):
    """Renomear a localização atualiza em cascata o campo
    `localizacao` dos eletrônicos."""
    # Cria CC + eletrônico com localização "Lab"
    cc = Contrato(centro_custo='LC01', descricao='Loc Cascade')
    async_db.add(cc)
    await async_db.flush()
    el = Eletronico(
        numero_serie='SN-LC01',
        numero_patrimonio='PAT-LC01',
        nome='Equip',
        tipo='Scanner',
        status='Interno',
        centro_custo='LC01',
        localizacao='Lab',
    )
    async_db.add(el)
    await async_db.flush()
    await async_db.refresh(el)

    # Cria a localização "Lab" via API
    create = await async_client.post(
        URL,
        json={'nome': 'Lab'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    loc_id = create.json()['id']

    # Renomeia
    resp = await async_client.put(
        f'{URL}{loc_id}',
        json={'nome': 'Laboratório TI'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    assert resp.status_code == HTTPStatus.OK

    # Eletrônico foi renomeado em cascata
    el_resp = await async_client.get(
        '/eletronicos/',
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    target = next(
        (e for e in el_resp.json()['eletronicos'] if e['id'] == el.id),
        None,
    )
    assert target is not None
    assert target['localizacao'] == 'Laboratório TI'


@pytest.mark.asyncio
@pytest.mark.routers
async def test_update_localizacao_duplicada_conflito(
    async_client, login_teste
):
    await async_client.post(
        URL,
        json={'nome': 'Existente1'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    create = await async_client.post(
        URL,
        json={'nome': 'Existente2'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    loc_id = create.json()['id']

    resp = await async_client.put(
        f'{URL}{loc_id}',
        json={'nome': 'Existente1'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.CONFLICT


@pytest.mark.asyncio
@pytest.mark.routers
async def test_update_localizacao_nao_encontrada(async_client, login_teste):
    resp = await async_client.put(
        f'{URL}99999',
        json={'nome': 'Inexistente'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.NOT_FOUND


# ─── DELETE (Admin only) ─────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_delete_localizacao_admin(async_client, login_teste):
    create = await async_client.post(
        URL,
        json={'nome': 'TempLoc'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    loc_id = create.json()['id']

    resp = await async_client.delete(
        f'{URL}{loc_id}',
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    assert resp.status_code == HTTPStatus.OK

    # Não aparece mais na lista
    list_resp = await async_client.get(
        URL, headers={'Authorization': f'Bearer {login_teste["token"]}'}
    )
    nomes = {loc['nome'] for loc in list_resp.json()['localizacoes']}
    assert 'TempLoc' not in nomes


@pytest.mark.asyncio
@pytest.mark.routers
async def test_delete_localizacao_nao_admin_proibido(
    async_client, async_db, login_teste
):
    create = await async_client.post(
        URL,
        json={'nome': 'NaoDeletavel'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    loc_id = create.json()['id']
    func, fsenha = await _criar_usuario(async_db)
    token = await _login(async_client, func.email, fsenha)

    resp = await async_client.delete(
        f'{URL}{loc_id}',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert resp.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
@pytest.mark.routers
async def test_delete_localizacao_nao_encontrada(async_client, login_teste):
    resp = await async_client.delete(
        f'{URL}99999',
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.NOT_FOUND
