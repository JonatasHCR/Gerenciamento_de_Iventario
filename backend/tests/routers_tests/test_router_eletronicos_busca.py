"""
Tests do filtro `campo` em GET /eletronicos/ — busca por campo
específico, por responsável, e filtro 'sem responsável'.
"""

from http import HTTPStatus
from itertools import count

import pytest

from backend.model.associacao_user_contrato import AssociacaoUserContrato
from backend.model.associacao_user_eletronico import AssociacaoUserEletronico
from backend.model.contratos import Contrato
from backend.model.eletronicos import Eletronico
from backend.model.user import User
from backend.security.security import Security

URL = '/eletronicos/'

_counter = count(1)


def _n():
    return next(_counter)


async def _criar_usuario(async_db, nome, tipo='Funcionario'):
    security = Security()
    senha = 'senha123'
    u = User(
        nome=nome,
        email=f'{nome}@busca.com',
        senha=security.get_senha_hash(senha),
        tipo=tipo,
    )
    async_db.add(u)
    await async_db.flush()
    await async_db.refresh(u)
    return u, senha


async def _criar_contrato(async_db, cc):
    c = Contrato(centro_custo=cc, descricao=f'Contrato {cc}')
    async_db.add(c)
    await async_db.flush()
    return c


async def _criar_eletronico(async_db, cc, **overrides):
    n = _n()
    defaults = dict(
        numero_serie=f'SN-BUS{n}',
        numero_patrimonio=f'PAT-BUS{n}',
        nome=f'EquipBus{n}',
        tipo='Notbook',
        status='Interno',
        centro_custo=cc,
    )
    defaults.update(overrides)
    e = Eletronico(**defaults)
    async_db.add(e)
    await async_db.flush()
    await async_db.refresh(e)
    return e


async def _associar_user_eletronico(async_db, user_id, eletronico_id):
    a = AssociacaoUserEletronico(
        user_id=user_id, eletronico_id=eletronico_id
    )
    async_db.add(a)
    await async_db.flush()


async def _associar_user_cc(async_db, user_id, cc, ocupacao='Funcionario'):
    a = AssociacaoUserContrato(
        user_id=user_id, centro_custo=cc, ocupacao=ocupacao
    )
    async_db.add(a)
    await async_db.flush()


# ─── campo=nome | numero_serie | numero_patrimonio ────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_busca_campo_nome(async_client, async_db, login_teste):
    await _criar_contrato(async_db, 'CB1')
    await _criar_eletronico(async_db, 'CB1', nome='Notebook XPS')
    await _criar_eletronico(async_db, 'CB1', nome='Impressora HP')

    resp = await async_client.get(
        URL,
        params={'q': 'XPS', 'campo': 'nome'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.OK
    items = resp.json()['eletronicos']
    assert all('XPS' in i['nome'] for i in items)
    assert len(items) == 1


@pytest.mark.asyncio
@pytest.mark.routers
async def test_busca_campo_numero_serie(
    async_client, async_db, login_teste
):
    await _criar_contrato(async_db, 'CB2')
    e = await _criar_eletronico(
        async_db, 'CB2', numero_serie='SN-UNIQ-123'
    )
    await _criar_eletronico(async_db, 'CB2')

    resp = await async_client.get(
        URL,
        params={'q': 'UNIQ', 'campo': 'numero_serie'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    items = resp.json()['eletronicos']
    assert len(items) == 1
    assert items[0]['id'] == e.id


@pytest.mark.asyncio
@pytest.mark.routers
async def test_busca_campo_invalido(async_client, login_teste):
    resp = await async_client.get(
        URL,
        params={'q': 'X', 'campo': 'inexistente'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    assert resp.status_code == HTTPStatus.BAD_REQUEST


# ─── campo=responsavel ────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_busca_por_responsavel(
    async_client, async_db, login_teste
):
    await _criar_contrato(async_db, 'CBR')
    user, _ = await _criar_usuario(async_db, 'JoaoSilva')
    e_com_resp = await _criar_eletronico(async_db, 'CBR')
    await _associar_user_eletronico(async_db, user.id, e_com_resp.id)
    e_sem_resp = await _criar_eletronico(async_db, 'CBR')  # noqa: F841

    resp = await async_client.get(
        URL,
        params={'q': 'Joao', 'campo': 'responsavel'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.OK
    items = resp.json()['eletronicos']
    ids = {i['id'] for i in items}
    assert e_com_resp.id in ids
    assert e_sem_resp.id not in ids


@pytest.mark.asyncio
@pytest.mark.routers
async def test_busca_por_responsavel_sem_termo_lista_com_resp(
    async_client, async_db, login_teste
):
    """campo=responsavel sem q lista todos que TÊM algum responsável."""
    await _criar_contrato(async_db, 'CBR2')
    user, _ = await _criar_usuario(async_db, 'Maria')
    e1 = await _criar_eletronico(async_db, 'CBR2')
    e2 = await _criar_eletronico(async_db, 'CBR2')
    await _associar_user_eletronico(async_db, user.id, e1.id)

    resp = await async_client.get(
        URL,
        params={'campo': 'responsavel'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    ids = {i['id'] for i in resp.json()['eletronicos']}
    assert e1.id in ids
    assert e2.id not in ids


@pytest.mark.asyncio
@pytest.mark.routers
async def test_busca_sem_responsavel(
    async_client, async_db, login_teste
):
    await _criar_contrato(async_db, 'CBSR')
    user, _ = await _criar_usuario(async_db, 'Carlos')
    e1 = await _criar_eletronico(async_db, 'CBSR')
    e2 = await _criar_eletronico(async_db, 'CBSR')
    await _associar_user_eletronico(async_db, user.id, e1.id)

    resp = await async_client.get(
        URL,
        params={'campo': 'sem_responsavel'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.OK
    ids = {i['id'] for i in resp.json()['eletronicos']}
    assert e1.id not in ids
    assert e2.id in ids


# ─── Filtros adicionais (status, tipo, centro_custo) ──────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_filtro_status(async_client, async_db, login_teste):
    await _criar_contrato(async_db, 'FS1')
    await _criar_eletronico(async_db, 'FS1', status='Interno')
    e_ext = await _criar_eletronico(async_db, 'FS1', status='Externo')

    resp = await async_client.get(
        URL,
        params={'status': ['Externo']},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    items = resp.json()['eletronicos']
    assert all(i['status'] == 'Externo' for i in items)
    assert any(i['id'] == e_ext.id for i in items)


@pytest.mark.asyncio
@pytest.mark.routers
async def test_filtro_tipo(async_client, async_db, login_teste):
    await _criar_contrato(async_db, 'FT1')
    e_imp = await _criar_eletronico(async_db, 'FT1', tipo='Impressora')
    await _criar_eletronico(async_db, 'FT1', tipo='Notbook')

    resp = await async_client.get(
        URL,
        params={'tipo': ['Impressora']},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    items = resp.json()['eletronicos']
    assert all(i['tipo'] == 'Impressora' for i in items)
    assert any(i['id'] == e_imp.id for i in items)


@pytest.mark.asyncio
@pytest.mark.routers
async def test_paginacao_page_size(async_client, async_db, login_teste):
    await _criar_contrato(async_db, 'PAG')
    for _ in range(7):
        await _criar_eletronico(async_db, 'PAG')

    resp = await async_client.get(
        URL,
        params={'page': 1, 'page_size': 3},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    body = resp.json()
    assert len(body['eletronicos']) == 3  # noqa: PLR2004
    assert body['page'] == 1
    assert body['page_size'] == 3  # noqa: PLR2004
    assert body['total'] >= 7  # noqa: PLR2004


# ─── Visibilidade per-papel (Funcionario só vê os próprios) ───────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_funcionario_ve_so_os_proprios(async_client, async_db):
    await _criar_contrato(async_db, 'FUN')
    func, fsenha = await _criar_usuario(async_db, 'fun_vis', 'Funcionario')
    await _associar_user_cc(async_db, func.id, 'FUN', 'Funcionario')

    e_meu = await _criar_eletronico(async_db, 'FUN')
    await _associar_user_eletronico(async_db, func.id, e_meu.id)
    e_alheio = await _criar_eletronico(async_db, 'FUN')

    login = await async_client.post(
        '/auth/login',
        data={'username': func.email, 'password': fsenha},
    )
    token = login.json()['access_token']

    resp = await async_client.get(
        URL,
        headers={'Authorization': f'Bearer {token}'},
    )

    ids = {i['id'] for i in resp.json()['eletronicos']}
    assert e_meu.id in ids
    assert e_alheio.id not in ids
