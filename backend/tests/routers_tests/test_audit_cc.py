"""
Tests do audit log para ações envolvendo CC e seus membros.
"""

from http import HTTPStatus
from itertools import count

import pytest

from backend.model.associacao_user_contrato import AssociacaoUserContrato
from backend.model.contratos import Contrato
from backend.model.user import User
from backend.security.security import Security

URL_AUDIT = '/audit-log/'
URL_CONTRATO = '/contratos/'
URL_ASSOC_CC = '/associacoes/contratos/'

_counter = count(1)


def _n():
    return next(_counter)


async def _criar_usuario(async_db, nome, tipo='Funcionario'):
    security = Security()
    senha = 'senha12345'
    u = User(
        nome=nome,
        email=f'{nome}@aucc.com',
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


async def _criar_contrato_db(async_db, cc):
    c = Contrato(centro_custo=cc, descricao=f'Contrato {cc}')
    async_db.add(c)
    await async_db.flush()
    return c


async def _assoc_db(async_db, user_id, cc, ocupacao):
    a = AssociacaoUserContrato(
        user_id=user_id, centro_custo=cc, ocupacao=ocupacao
    )
    async_db.add(a)
    await async_db.flush()


def _find_audit(items, action: str, payload_predicate=None):
    for i in items:
        if i['action'] == action and (
            payload_predicate is None
            or payload_predicate(i['payload'] or {})
        ):
            return i
    return None


# ─── CC create/update/delete ──────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_contrato_create_gera_audit(
    async_client, login_teste
):
    resp = await async_client.post(
        URL_CONTRATO,
        json={'centro_custo': 'AC01', 'descricao': 'Novo CC'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    assert resp.status_code == HTTPStatus.CREATED

    audit = await async_client.get(
        URL_AUDIT,
        params={'action': 'contrato.create'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    entry = _find_audit(
        audit.json()['items'],
        'contrato.create',
        lambda p: p.get('centro_custo') == 'AC01',
    )
    assert entry is not None
    assert entry['payload']['descricao'] == 'Novo CC'

    # E também gera audit de cc.membro.add (criador auto-associado)
    audit_membro = await async_client.get(
        URL_AUDIT,
        params={'action': 'cc.membro.add'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    membro = _find_audit(
        audit_membro.json()['items'],
        'cc.membro.add',
        lambda p: p.get('centro_custo') == 'AC01'
        and p.get('via_criacao_cc') is True,
    )
    assert membro is not None


@pytest.mark.asyncio
@pytest.mark.routers
async def test_contrato_update_gera_audit(
    async_client, async_db, login_teste
):
    await _criar_contrato_db(async_db, 'AC02')

    resp = await async_client.put(
        f'{URL_CONTRATO}AC02',
        json={'centro_custo': 'AC02', 'descricao': 'Atualizado'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    assert resp.status_code == HTTPStatus.OK

    audit = await async_client.get(
        URL_AUDIT,
        params={'action': 'contrato.update'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    entry = _find_audit(
        audit.json()['items'],
        'contrato.update',
        lambda p: p.get('centro_custo') == 'AC02',
    )
    assert entry is not None
    assert entry['payload']['depois']['descricao'] == 'Atualizado'


@pytest.mark.asyncio
@pytest.mark.routers
async def test_contrato_delete_gera_audit(
    async_client, async_db, login_teste
):
    await _criar_contrato_db(async_db, 'AC03')

    resp = await async_client.delete(
        f'{URL_CONTRATO}AC03',
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    assert resp.status_code == HTTPStatus.OK

    audit = await async_client.get(
        URL_AUDIT,
        params={'action': 'contrato.delete'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    entry = _find_audit(
        audit.json()['items'],
        'contrato.delete',
        lambda p: p.get('centro_custo') == 'AC03',
    )
    assert entry is not None


# ─── CC membros ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_cc_membro_add_gera_audit(
    async_client, async_db, login_teste
):
    await _criar_contrato_db(async_db, 'MEM1')
    # Pre-popula com 1 membro pra evitar bypass "primeiro membro"
    gestor, _ = await _criar_usuario(async_db, 'g_mem1', 'Gestor')
    await _assoc_db(async_db, gestor.id, 'MEM1', 'Gestor')
    novo, _ = await _criar_usuario(async_db, 'novo_mem1')

    resp = await async_client.post(
        URL_ASSOC_CC,
        json={
            'user_id': novo.id,
            'centro_custo': 'MEM1',
            'ocupacao': 'Funcionario',
        },
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    assert resp.status_code == HTTPStatus.CREATED

    audit = await async_client.get(
        URL_AUDIT,
        params={'action': 'cc.membro.add'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    entry = _find_audit(
        audit.json()['items'],
        'cc.membro.add',
        lambda p: p.get('centro_custo') == 'MEM1'
        and p.get('usuario_id') == novo.id
        and p.get('via_criacao_cc') is False,
    )
    assert entry is not None
    assert entry['payload']['ocupacao'] == 'Funcionario'


@pytest.mark.asyncio
@pytest.mark.routers
async def test_cc_membro_ocupacao_change_gera_audit(
    async_client, async_db, login_teste
):
    await _criar_contrato_db(async_db, 'MEM2')
    alvo, _ = await _criar_usuario(async_db, 'alvo_oc')
    await _assoc_db(async_db, alvo.id, 'MEM2', 'Funcionario')

    resp = await async_client.put(
        f'{URL_ASSOC_CC}{alvo.id}/MEM2',
        json={
            'user_id': alvo.id,
            'centro_custo': 'MEM2',
            'ocupacao': 'Subgestor',
        },
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    assert resp.status_code == HTTPStatus.OK

    audit = await async_client.get(
        URL_AUDIT,
        params={'action': 'cc.membro.ocupacao_change'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    entry = _find_audit(
        audit.json()['items'],
        'cc.membro.ocupacao_change',
        lambda p: p.get('usuario_id') == alvo.id,
    )
    assert entry is not None
    assert entry['payload']['de'] == 'Funcionario'
    assert entry['payload']['para'] == 'Subgestor'


@pytest.mark.asyncio
@pytest.mark.routers
async def test_cc_membro_remove_admin_gera_audit(
    async_client, async_db, login_teste
):
    await _criar_contrato_db(async_db, 'MEM3')
    gestor, _ = await _criar_usuario(async_db, 'g_mem3', 'Gestor')
    await _assoc_db(async_db, gestor.id, 'MEM3', 'Gestor')
    alvo, _ = await _criar_usuario(async_db, 'alvo_rem')
    await _assoc_db(async_db, alvo.id, 'MEM3', 'Funcionario')

    resp = await async_client.delete(
        f'{URL_ASSOC_CC}{alvo.id}/MEM3',
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    assert resp.status_code == HTTPStatus.OK

    audit = await async_client.get(
        URL_AUDIT,
        params={'action': 'cc.membro.remove'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    entry = _find_audit(
        audit.json()['items'],
        'cc.membro.remove',
        lambda p: p.get('usuario_id') == alvo.id,
    )
    assert entry is not None
    assert entry['payload']['ocupacao'] == 'Funcionario'


@pytest.mark.asyncio
@pytest.mark.routers
async def test_cc_membro_self_remove_gera_audit(
    async_client, async_db, login_teste
):
    await _criar_contrato_db(async_db, 'MEM4')
    # Pre-popula com um Gestor pra não bloquear o self-remove
    gestor, _ = await _criar_usuario(async_db, 'g_mem4', 'Gestor')
    await _assoc_db(async_db, gestor.id, 'MEM4', 'Gestor')
    sair, ssenha = await _criar_usuario(async_db, 'self_rem')
    await _assoc_db(async_db, sair.id, 'MEM4', 'Funcionario')
    token = await _login(async_client, sair.email, ssenha)

    resp = await async_client.delete(
        f'{URL_ASSOC_CC}{sair.id}/MEM4',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert resp.status_code == HTTPStatus.OK

    audit = await async_client.get(
        URL_AUDIT,
        params={'action': 'cc.membro.self_remove'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    entry = _find_audit(
        audit.json()['items'],
        'cc.membro.self_remove',
        lambda p: p.get('usuario_id') == sair.id,
    )
    assert entry is not None
