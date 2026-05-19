"""
Tests do audit log + da restrição de domínio no auto-registro.
"""

from http import HTTPStatus
from itertools import count

import pytest

from backend.model.associacao_user_contrato import AssociacaoUserContrato
from backend.model.contratos import Contrato
from backend.model.eletronicos import Eletronico
from backend.model.user import User
from backend.security.security import Security

URL = '/audit-log/'

_counter = count(1)


def _n():
    return next(_counter)


# ─── helpers ────────────────────────────────────────────────────────────────


async def _criar_usuario(async_db, nome, tipo='Funcionario', email=None):
    security = Security()
    senha = 'senha12345'
    u = User(
        nome=nome,
        email=email or f'{nome}@audit.com',
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


async def _criar_contrato(async_db, cc=None):
    cc = cc or f'AU{_n():03d}'
    c = Contrato(centro_custo=cc, descricao=f'Contrato {cc}')
    async_db.add(c)
    await async_db.flush()
    return c


async def _assoc(async_db, user_id, cc, ocupacao):
    a = AssociacaoUserContrato(
        user_id=user_id, centro_custo=cc, ocupacao=ocupacao
    )
    async_db.add(a)
    await async_db.flush()


async def _criar_eletronico(async_db, cc):
    n = _n()
    e = Eletronico(
        numero_serie=f'SN-AU{n}',
        numero_patrimonio=f'PAT-AU{n}',
        nome=f'EquipAu{n}',
        tipo='Notbook',
        status='Interno',
        centro_custo=cc,
    )
    async_db.add(e)
    await async_db.flush()
    await async_db.refresh(e)
    return e


# ─── /audit-log/ — listagem + permissões ────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_audit_log_admin_lista_vazia_inicialmente(
    async_client, login_teste
):
    resp = await async_client.get(
        URL,
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    assert resp.status_code == HTTPStatus.OK
    body = resp.json()
    assert 'items' in body
    assert 'total' in body


@pytest.mark.asyncio
@pytest.mark.routers
async def test_audit_log_nao_admin_403(async_client, async_db):
    func, fsenha = await _criar_usuario(async_db, 'fa1')
    token = await _login(async_client, func.email, fsenha)

    resp = await async_client.get(
        URL, headers={'Authorization': f'Bearer {token}'}
    )

    assert resp.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
@pytest.mark.routers
async def test_audit_log_tecnico_ti_403(async_client, async_db):
    """Tecnico_TI também é bloqueado — audit log é só pra Admin."""
    ti, tsenha = await _criar_usuario(async_db, 'fa2', 'Tecnico_TI')
    token = await _login(async_client, ti.email, tsenha)

    resp = await async_client.get(
        URL, headers={'Authorization': f'Bearer {token}'}
    )

    assert resp.status_code == HTTPStatus.FORBIDDEN


# ─── Eventos auditáveis ─────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_cessao_create_gera_audit(
    async_client, async_db, login_teste
):
    c = await _criar_contrato(async_db)
    e = await _criar_eletronico(async_db, c.centro_custo)

    create_resp = await async_client.post(
        '/cessoes/',
        json={
            'eletronico_ids': [e.id],
            'responsavel': 'X',
            'centro_custo_destino': c.centro_custo,
        },
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    cessao_id = create_resp.json()['id']

    resp = await async_client.get(
        URL,
        params={'action': 'cessao.create'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    items = resp.json()['items']
    matching = [i for i in items if i['target_id'] == cessao_id]
    assert len(matching) == 1
    assert matching[0]['target_type'] == 'cessao'
    assert matching[0]['payload']['responsavel'] == 'X'


@pytest.mark.asyncio
@pytest.mark.routers
async def test_cessao_devolver_gera_audit(
    async_client, async_db, login_teste
):
    c = await _criar_contrato(async_db)
    e = await _criar_eletronico(async_db, c.centro_custo)
    create_resp = await async_client.post(
        '/cessoes/',
        json={
            'eletronico_ids': [e.id],
            'responsavel': 'X',
            'centro_custo_destino': c.centro_custo,
        },
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    cessao_id = create_resp.json()['id']

    await async_client.put(
        f'/cessoes/{cessao_id}/devolver',
        json={'eletronico_ids': [e.id]},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    resp = await async_client.get(
        URL,
        params={'action': 'cessao.devolver', 'target_type': 'cessao'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    items = [i for i in resp.json()['items'] if i['target_id'] == cessao_id]
    assert len(items) == 1
    assert items[0]['payload']['lote'] == 1
    assert items[0]['payload']['parcial'] is False


@pytest.mark.asyncio
@pytest.mark.routers
async def test_cessao_delete_gera_audit(
    async_client, async_db, login_teste
):
    c = await _criar_contrato(async_db)
    e = await _criar_eletronico(async_db, c.centro_custo)
    create_resp = await async_client.post(
        '/cessoes/',
        json={
            'eletronico_ids': [e.id],
            'responsavel': 'X',
            'centro_custo_destino': c.centro_custo,
        },
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    cessao_id = create_resp.json()['id']

    await async_client.delete(
        f'/cessoes/{cessao_id}',
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    resp = await async_client.get(
        URL,
        params={'action': 'cessao.delete'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    items = [
        i for i in resp.json()['items'] if i['target_id'] == cessao_id
    ]
    assert len(items) == 1


@pytest.mark.asyncio
@pytest.mark.routers
async def test_solicitacao_aprovar_gera_audit(
    async_client, async_db, login_teste
):
    await _criar_contrato(async_db, 'AUS')
    func, fsenha = await _criar_usuario(async_db, 'sol_audit')
    ftoken = await _login(async_client, func.email, fsenha)

    create_resp = await async_client.post(
        '/solicitacoes/entrada-cc',
        json={'centro_custo': 'AUS', 'ocupacao_solicitada': 'Funcionario'},
        headers={'Authorization': f'Bearer {ftoken}'},
    )
    sol_id = create_resp.json()['id']

    await async_client.put(
        f'/solicitacoes/{sol_id}/aprovar',
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    resp = await async_client.get(
        URL,
        params={'action': 'solicitacao.aprovar'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    items = [i for i in resp.json()['items'] if i['target_id'] == sol_id]
    assert len(items) == 1
    assert items[0]['payload']['tipo'] == 'entrada_cc'


@pytest.mark.asyncio
@pytest.mark.routers
async def test_solicitacao_rejeitar_gera_audit(
    async_client, async_db, login_teste
):
    await _criar_contrato(async_db, 'AUR')
    func, fsenha = await _criar_usuario(async_db, 'sol_rej')
    ftoken = await _login(async_client, func.email, fsenha)
    create_resp = await async_client.post(
        '/solicitacoes/entrada-cc',
        json={'centro_custo': 'AUR', 'ocupacao_solicitada': 'Funcionario'},
        headers={'Authorization': f'Bearer {ftoken}'},
    )
    sol_id = create_resp.json()['id']

    await async_client.put(
        f'/solicitacoes/{sol_id}/rejeitar',
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    resp = await async_client.get(
        URL,
        params={'action': 'solicitacao.rejeitar'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    items = [i for i in resp.json()['items'] if i['target_id'] == sol_id]
    assert len(items) == 1


@pytest.mark.asyncio
@pytest.mark.routers
async def test_solicitacao_admin_delete_gera_audit(
    async_client, async_db, login_teste
):
    await _criar_contrato(async_db, 'AUD')
    func, fsenha = await _criar_usuario(async_db, 'sol_del')
    ftoken = await _login(async_client, func.email, fsenha)
    create_resp = await async_client.post(
        '/solicitacoes/entrada-cc',
        json={'centro_custo': 'AUD', 'ocupacao_solicitada': 'Funcionario'},
        headers={'Authorization': f'Bearer {ftoken}'},
    )
    sol_id = create_resp.json()['id']

    await async_client.delete(
        f'/solicitacoes/{sol_id}',
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    resp = await async_client.get(
        URL,
        params={'action': 'solicitacao.delete'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    items = [i for i in resp.json()['items'] if i['target_id'] == sol_id]
    assert len(items) == 1


@pytest.mark.asyncio
@pytest.mark.routers
async def test_user_delete_gera_audit(
    async_client, async_db, login_teste
):
    alvo, _ = await _criar_usuario(async_db, 'alvo_del')

    await async_client.delete(
        f'/users/{alvo.id}',
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    resp = await async_client.get(
        URL,
        params={'action': 'user.delete'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    items = [i for i in resp.json()['items'] if i['target_id'] == alvo.id]
    assert len(items) == 1
    assert items[0]['payload']['email'] == 'alvo_del@audit.com'


@pytest.mark.asyncio
@pytest.mark.routers
async def test_user_tipo_change_gera_audit(
    async_client, async_db, login_teste
):
    alvo, _ = await _criar_usuario(async_db, 'alvo_tipo')

    await async_client.put(
        f'/users/{alvo.id}',
        json={'tipo': 'Gestor'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    resp = await async_client.get(
        URL,
        params={'action': 'user.tipo_change'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    items = [i for i in resp.json()['items'] if i['target_id'] == alvo.id]
    assert len(items) == 1
    assert items[0]['payload']['de'] == 'Funcionario'
    assert items[0]['payload']['para'] == 'Gestor'


@pytest.mark.asyncio
@pytest.mark.routers
async def test_audit_log_filtra_por_user_id(
    async_client, async_db, login_teste
):
    alvo, _ = await _criar_usuario(async_db, 'alvo_filter')
    await async_client.delete(
        f'/users/{alvo.id}',
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    resp = await async_client.get(
        URL,
        params={'user_id': 999999},  # ninguém
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    assert resp.json()['items'] == []
