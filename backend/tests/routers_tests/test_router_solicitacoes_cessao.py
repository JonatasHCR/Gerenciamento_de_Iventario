"""
Tests para o tipo 'cessao' de Solicitacao + cancelar/excluir por Admin
em qualquer status. Complementa test_router_solicitacoes.py.
"""

from http import HTTPStatus
from itertools import count

import pytest

from backend.model.associacao_user_contrato import AssociacaoUserContrato
from backend.model.contratos import Contrato
from backend.model.eletronicos import Eletronico
from backend.model.user import User
from backend.security.security import Security

URL = '/solicitacoes'

_counter = count(1)


def _n():
    return next(_counter)


async def _criar_usuario(async_db, nome, tipo='Funcionario'):
    security = Security()
    senha = 'senha123'
    u = User(
        nome=nome,
        email=f'{nome}@solces.com',
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


async def _criar_contrato(async_db, cc):
    c = Contrato(centro_custo=cc, descricao=f'Contrato {cc}')
    async_db.add(c)
    await async_db.flush()
    return c


async def _associar(async_db, user_id, cc, ocupacao):
    a = AssociacaoUserContrato(
        user_id=user_id, centro_custo=cc, ocupacao=ocupacao
    )
    async_db.add(a)
    await async_db.flush()


async def _criar_eletronico(async_db, cc, status='Interno'):
    n = _n()
    e = Eletronico(
        numero_serie=f'SN-SC{n}',
        numero_patrimonio=f'PAT-SC{n}',
        nome=f'EquipSC{n}',
        tipo='Notbook',
        status=status,
        centro_custo=cc,
    )
    async_db.add(e)
    await async_db.flush()
    await async_db.refresh(e)
    return e


# ─── POST /solicitacoes/cessao ─────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_solicitacao_cessao_subgestor(async_client, async_db):
    await _criar_contrato(async_db, 'SC01')
    await _criar_contrato(async_db, 'SC02')
    subg, ssenha = await _criar_usuario(async_db, 'sc_subg', 'Subgestor')
    await _associar(async_db, subg.id, 'SC01', 'Subgestor')
    e = await _criar_eletronico(async_db, 'SC01')
    token = await _login(async_client, subg.email, ssenha)

    resp = await async_client.post(
        f'{URL}/cessao',
        json={
            'eletronico_ids': [e.id],
            'responsavel': 'Receptor',
            'centro_custo_destino': 'SC02',
        },
        headers={'Authorization': f'Bearer {token}'},
    )

    assert resp.status_code == HTTPStatus.CREATED
    body = resp.json()
    assert body['tipo'] == 'cessao'
    assert body['status'] == 'pendente'
    assert body['centro_custo'] == 'SC01'
    assert body['centro_custo_destino'] == 'SC02'
    assert body['responsavel'] == 'Receptor'
    assert len(body['eletronicos']) == 1


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_solicitacao_cessao_funcionario_proibido(
    async_client, async_db
):
    await _criar_contrato(async_db, 'SCF')
    func, fsenha = await _criar_usuario(async_db, 'sc_func')
    await _associar(async_db, func.id, 'SCF', 'Funcionario')
    e = await _criar_eletronico(async_db, 'SCF')
    token = await _login(async_client, func.email, fsenha)

    resp = await async_client.post(
        f'{URL}/cessao',
        json={
            'eletronico_ids': [e.id],
            'responsavel': 'X',
            'centro_custo_destino': 'SCF',
        },
        headers={'Authorization': f'Bearer {token}'},
    )

    assert resp.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_solicitacao_cessao_admin_bloqueado(
    async_client, async_db, login_teste
):
    """Admin não usa este endpoint — cede direto via /cessoes."""
    await _criar_contrato(async_db, 'SCA')
    e = await _criar_eletronico(async_db, 'SCA')

    resp = await async_client.post(
        f'{URL}/cessao',
        json={
            'eletronico_ids': [e.id],
            'responsavel': 'X',
            'centro_custo_destino': 'SCA',
        },
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.BAD_REQUEST


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_solicitacao_cessao_multi_cc_origem(
    async_client, async_db
):
    """Itens devem ser de um único CC de origem."""
    await _criar_contrato(async_db, 'MC1')
    await _criar_contrato(async_db, 'MC2')
    subg, ssenha = await _criar_usuario(async_db, 'sc_mc', 'Subgestor')
    await _associar(async_db, subg.id, 'MC1', 'Subgestor')
    await _associar(async_db, subg.id, 'MC2', 'Subgestor')
    e1 = await _criar_eletronico(async_db, 'MC1')
    e2 = await _criar_eletronico(async_db, 'MC2')
    token = await _login(async_client, subg.email, ssenha)

    resp = await async_client.post(
        f'{URL}/cessao',
        json={
            'eletronico_ids': [e1.id, e2.id],
            'responsavel': 'X',
            'centro_custo_destino': 'MC1',
        },
        headers={'Authorization': f'Bearer {token}'},
    )

    assert resp.status_code == HTTPStatus.BAD_REQUEST


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_solicitacao_cessao_item_externo(
    async_client, async_db
):
    await _criar_contrato(async_db, 'CEX')
    subg, ssenha = await _criar_usuario(async_db, 'sc_ex', 'Subgestor')
    await _associar(async_db, subg.id, 'CEX', 'Subgestor')
    e = await _criar_eletronico(async_db, 'CEX', status='Externo')
    token = await _login(async_client, subg.email, ssenha)

    resp = await async_client.post(
        f'{URL}/cessao',
        json={
            'eletronico_ids': [e.id],
            'responsavel': 'X',
            'centro_custo_destino': 'CEX',
        },
        headers={'Authorization': f'Bearer {token}'},
    )

    assert resp.status_code == HTTPStatus.CONFLICT


# ─── Aprovação/rejeição de cessao ──────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_aprovar_solicitacao_cessao_cria_cessao(
    async_client, async_db
):
    """Aprovar pelo Gestor do CC cria a Cessao real."""
    await _criar_contrato(async_db, 'APC')
    gestor, gsenha = await _criar_usuario(async_db, 'g_apc', 'Gestor')
    await _associar(async_db, gestor.id, 'APC', 'Gestor')
    subg, ssenha = await _criar_usuario(async_db, 'sg_apc', 'Subgestor')
    await _associar(async_db, subg.id, 'APC', 'Subgestor')
    e = await _criar_eletronico(async_db, 'APC')
    stoken = await _login(async_client, subg.email, ssenha)

    create_resp = await async_client.post(
        f'{URL}/cessao',
        json={
            'eletronico_ids': [e.id],
            'responsavel': 'RespAPC',
            'centro_custo_destino': 'APC',
        },
        headers={'Authorization': f'Bearer {stoken}'},
    )
    sol_id = create_resp.json()['id']
    gtoken = await _login(async_client, gestor.email, gsenha)

    resp = await async_client.put(
        f'{URL}/{sol_id}/aprovar',
        headers={'Authorization': f'Bearer {gtoken}'},
    )

    assert resp.status_code == HTTPStatus.OK
    assert resp.json()['status'] == 'aprovada'

    list_cessoes = await async_client.get(
        '/cessoes/', headers={'Authorization': f'Bearer {gtoken}'}
    )
    cessoes = list_cessoes.json()['cessoes']
    assert any(c['responsavel'] == 'RespAPC' for c in cessoes)


@pytest.mark.asyncio
@pytest.mark.routers
async def test_aprovar_solicitacao_cessao_subgestor_proibido(
    async_client, async_db
):
    """Só Gestor ou Admin aprovam — Subgestor não."""
    await _criar_contrato(async_db, 'ASP')
    subg, ssenha = await _criar_usuario(async_db, 'sg_asp', 'Subgestor')
    await _associar(async_db, subg.id, 'ASP', 'Subgestor')
    subg2, s2senha = await _criar_usuario(async_db, 'sg_asp2', 'Subgestor')
    await _associar(async_db, subg2.id, 'ASP', 'Subgestor')
    e = await _criar_eletronico(async_db, 'ASP')
    s1tok = await _login(async_client, subg.email, ssenha)

    create_resp = await async_client.post(
        f'{URL}/cessao',
        json={
            'eletronico_ids': [e.id],
            'responsavel': 'X',
            'centro_custo_destino': 'ASP',
        },
        headers={'Authorization': f'Bearer {s1tok}'},
    )
    sol_id = create_resp.json()['id']
    s2tok = await _login(async_client, subg2.email, s2senha)

    resp = await async_client.put(
        f'{URL}/{sol_id}/aprovar',
        headers={'Authorization': f'Bearer {s2tok}'},
    )

    assert resp.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
@pytest.mark.routers
async def test_rejeitar_solicitacao_cessao_nao_cria_cessao(
    async_client, async_db
):
    await _criar_contrato(async_db, 'REJ')
    gestor, gsenha = await _criar_usuario(async_db, 'g_rej', 'Gestor')
    await _associar(async_db, gestor.id, 'REJ', 'Gestor')
    subg, ssenha = await _criar_usuario(async_db, 'sg_rej', 'Subgestor')
    await _associar(async_db, subg.id, 'REJ', 'Subgestor')
    e = await _criar_eletronico(async_db, 'REJ')
    stoken = await _login(async_client, subg.email, ssenha)

    create_resp = await async_client.post(
        f'{URL}/cessao',
        json={
            'eletronico_ids': [e.id],
            'responsavel': 'RespREJ',
            'centro_custo_destino': 'REJ',
        },
        headers={'Authorization': f'Bearer {stoken}'},
    )
    sol_id = create_resp.json()['id']
    gtoken = await _login(async_client, gestor.email, gsenha)

    resp = await async_client.put(
        f'{URL}/{sol_id}/rejeitar',
        headers={'Authorization': f'Bearer {gtoken}'},
    )

    assert resp.status_code == HTTPStatus.OK
    assert resp.json()['status'] == 'rejeitada'

    list_cessoes = await async_client.get(
        '/cessoes/', headers={'Authorization': f'Bearer {gtoken}'}
    )
    assert all(
        c['responsavel'] != 'RespREJ'
        for c in list_cessoes.json()['cessoes']
    )


# ─── Exclusão (Admin em qualquer status) ───────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_admin_exclui_solicitacao_aprovada(
    async_client, async_db, login_teste
):
    """Admin apaga solicitação em qualquer status, inclusive aprovada."""
    await _criar_contrato(async_db, 'ADX')
    func, fsenha = await _criar_usuario(async_db, 'func_adx')
    ftoken = await _login(async_client, func.email, fsenha)

    create_resp = await async_client.post(
        f'{URL}/entrada-cc',
        json={'centro_custo': 'ADX', 'ocupacao_solicitada': 'Funcionario'},
        headers={'Authorization': f'Bearer {ftoken}'},
    )
    sol_id = create_resp.json()['id']
    await async_client.put(
        f'{URL}/{sol_id}/aprovar',
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    resp = await async_client.delete(
        f'{URL}/{sol_id}',
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.OK


@pytest.mark.asyncio
@pytest.mark.routers
async def test_solicitante_nao_apaga_solicitacao_aprovada(
    async_client, async_db, login_teste
):
    """Solicitante não cancela uma solicitação que já foi aprovada."""
    await _criar_contrato(async_db, 'NAX')
    func, fsenha = await _criar_usuario(async_db, 'func_nax')
    ftoken = await _login(async_client, func.email, fsenha)
    create_resp = await async_client.post(
        f'{URL}/entrada-cc',
        json={'centro_custo': 'NAX', 'ocupacao_solicitada': 'Funcionario'},
        headers={'Authorization': f'Bearer {ftoken}'},
    )
    sol_id = create_resp.json()['id']
    await async_client.put(
        f'{URL}/{sol_id}/aprovar',
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    resp = await async_client.delete(
        f'{URL}/{sol_id}',
        headers={'Authorization': f'Bearer {ftoken}'},
    )

    assert resp.status_code == HTTPStatus.BAD_REQUEST


@pytest.mark.asyncio
@pytest.mark.routers
async def test_admin_exclui_solicitacao_rejeitada(
    async_client, async_db, login_teste
):
    await _criar_contrato(async_db, 'AXR')
    func, fsenha = await _criar_usuario(async_db, 'func_axr')
    ftoken = await _login(async_client, func.email, fsenha)
    create_resp = await async_client.post(
        f'{URL}/entrada-cc',
        json={'centro_custo': 'AXR', 'ocupacao_solicitada': 'Funcionario'},
        headers={'Authorization': f'Bearer {ftoken}'},
    )
    sol_id = create_resp.json()['id']
    await async_client.put(
        f'{URL}/{sol_id}/rejeitar',
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    resp = await async_client.delete(
        f'{URL}/{sol_id}',
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.OK
