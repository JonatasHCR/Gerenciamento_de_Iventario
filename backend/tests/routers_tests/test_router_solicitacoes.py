from http import HTTPStatus

import pytest

from backend.model.associacao_user_contrato import AssociacaoUserContrato
from backend.model.contratos import Contrato
from backend.model.user import User
from backend.security.security import Security

URL = '/solicitacoes'


# ─── helpers ─────────────────────────────────────────────────────────────────


async def _criar_usuario(async_db, nome, tipo='Funcionario'):
    security = Security()
    senha = 'senha123'
    u = User(
        nome=nome,
        email=f'{nome}@sol.com',
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


async def _criar_contrato(async_db, cc='CC01'):
    c = Contrato(centro_custo=cc, descricao=f'Contrato {cc}')
    async_db.add(c)
    await async_db.flush()
    return c


async def _associar(async_db, user_id, cc, ocupacao='Gestor'):
    a = AssociacaoUserContrato(
        user_id=user_id, centro_custo=cc, ocupacao=ocupacao
    )
    async_db.add(a)
    await async_db.flush()


# ─── entrada-cc ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_entrada_cc(async_client, async_db):
    await _criar_contrato(async_db)
    func, fsenha = await _criar_usuario(async_db, 'func1')
    token = await _login(async_client, func.email, fsenha)

    resp = await async_client.post(
        f'{URL}/entrada-cc',
        json={
            'centro_custo': 'CC01',
            'ocupacao_solicitada': 'Funcionario',
        },
        headers={'Authorization': f'Bearer {token}'},
    )

    assert resp.status_code == HTTPStatus.CREATED
    data = resp.json()
    assert data['tipo'] == 'entrada_cc'
    assert data['status'] == 'pendente'
    assert data['convidado_por_id'] is None


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_entrada_cc_cc_nao_encontrado(async_client, async_db):
    func, fsenha = await _criar_usuario(async_db, 'func2')
    token = await _login(async_client, func.email, fsenha)

    resp = await async_client.post(
        f'{URL}/entrada-cc',
        json={
            'centro_custo': 'XXXX',
            'ocupacao_solicitada': 'Funcionario',
        },
        headers={'Authorization': f'Bearer {token}'},
    )

    assert resp.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_entrada_cc_duplicada(async_client, async_db):
    await _criar_contrato(async_db)
    func, fsenha = await _criar_usuario(async_db, 'func3')
    token = await _login(async_client, func.email, fsenha)
    payload = {'centro_custo': 'CC01', 'ocupacao_solicitada': 'Funcionario'}

    await async_client.post(
        f'{URL}/entrada-cc',
        json=payload,
        headers={'Authorization': f'Bearer {token}'},
    )
    resp = await async_client.post(
        f'{URL}/entrada-cc',
        json=payload,
        headers={'Authorization': f'Bearer {token}'},
    )

    assert resp.status_code == HTTPStatus.CONFLICT


# ─── convite-cc ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_convite_cc_gestor(async_client, async_db):
    await _criar_contrato(async_db)
    gestor, gsenha = await _criar_usuario(async_db, 'gest1', 'Gestor')
    await _associar(async_db, gestor.id, 'CC01', 'Gestor')
    convidado, _ = await _criar_usuario(async_db, 'conv1')
    gtoken = await _login(async_client, gestor.email, gsenha)

    resp = await async_client.post(
        f'{URL}/convite-cc',
        json={
            'solicitante_id': convidado.id,
            'centro_custo': 'CC01',
            'ocupacao_solicitada': 'Funcionario',
        },
        headers={'Authorization': f'Bearer {gtoken}'},
    )

    assert resp.status_code == HTTPStatus.CREATED
    assert resp.json()['convidado_por_id'] == gestor.id


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_convite_cc_nao_autorizado(async_client, async_db):
    await _criar_contrato(async_db)
    func, fsenha = await _criar_usuario(async_db, 'func4')
    convidado, _ = await _criar_usuario(async_db, 'conv2')
    ftoken = await _login(async_client, func.email, fsenha)

    resp = await async_client.post(
        f'{URL}/convite-cc',
        json={
            'solicitante_id': convidado.id,
            'centro_custo': 'CC01',
            'ocupacao_solicitada': 'Funcionario',
        },
        headers={'Authorization': f'Bearer {ftoken}'},
    )

    assert resp.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_convite_cc_subgestor_funcionario(
    async_client, async_db
):
    await _criar_contrato(async_db)
    subg, ssenha = await _criar_usuario(async_db, 'subg1', 'Subgestor')
    await _associar(async_db, subg.id, 'CC01', 'Subgestor')
    convidado, _ = await _criar_usuario(async_db, 'conv3')
    stoken = await _login(async_client, subg.email, ssenha)

    resp = await async_client.post(
        f'{URL}/convite-cc',
        json={
            'solicitante_id': convidado.id,
            'centro_custo': 'CC01',
            'ocupacao_solicitada': 'Funcionario',
        },
        headers={'Authorization': f'Bearer {stoken}'},
    )

    assert resp.status_code == HTTPStatus.CREATED


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_convite_cc_subgestor_cargo_maior(
    async_client, async_db
):
    await _criar_contrato(async_db)
    subg, ssenha = await _criar_usuario(async_db, 'subg2', 'Subgestor')
    await _associar(async_db, subg.id, 'CC01', 'Subgestor')
    convidado, _ = await _criar_usuario(async_db, 'conv4')
    stoken = await _login(async_client, subg.email, ssenha)

    resp = await async_client.post(
        f'{URL}/convite-cc',
        json={
            'solicitante_id': convidado.id,
            'centro_custo': 'CC01',
            'ocupacao_solicitada': 'Gestor',
        },
        headers={'Authorization': f'Bearer {stoken}'},
    )

    assert resp.status_code == HTTPStatus.FORBIDDEN


# ─── cargo-inicial ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_cargo_inicial(async_client, async_db):
    func, fsenha = await _criar_usuario(async_db, 'func5')
    token = await _login(async_client, func.email, fsenha)

    resp = await async_client.post(
        f'{URL}/cargo-inicial',
        json={'cargo_solicitado': 'Gestor'},
        headers={'Authorization': f'Bearer {token}'},
    )

    assert resp.status_code == HTTPStatus.CREATED
    assert resp.json()['tipo'] == 'cargo_inicial'
    assert resp.json()['cargo_solicitado'] == 'Gestor'


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_cargo_inicial_duplicada(async_client, async_db):
    func, fsenha = await _criar_usuario(async_db, 'func6')
    token = await _login(async_client, func.email, fsenha)
    payload = {'cargo_solicitado': 'Gestor'}

    await async_client.post(
        f'{URL}/cargo-inicial',
        json=payload,
        headers={'Authorization': f'Bearer {token}'},
    )
    resp = await async_client.post(
        f'{URL}/cargo-inicial',
        json=payload,
        headers={'Authorization': f'Bearer {token}'},
    )

    assert resp.status_code == HTTPStatus.CONFLICT


# ─── aprovar ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_aprovar_entrada_cc_gestor(async_client, async_db):
    await _criar_contrato(async_db)
    gestor, gsenha = await _criar_usuario(async_db, 'gest2', 'Gestor')
    await _associar(async_db, gestor.id, 'CC01', 'Gestor')
    func, fsenha = await _criar_usuario(async_db, 'func7')
    gtoken = await _login(async_client, gestor.email, gsenha)
    ftoken = await _login(async_client, func.email, fsenha)

    resp = await async_client.post(
        f'{URL}/entrada-cc',
        json={'centro_custo': 'CC01', 'ocupacao_solicitada': 'Funcionario'},
        headers={'Authorization': f'Bearer {ftoken}'},
    )
    sol_id = resp.json()['id']

    resp = await async_client.put(
        f'{URL}/{sol_id}/aprovar',
        headers={'Authorization': f'Bearer {gtoken}'},
    )

    assert resp.status_code == HTTPStatus.OK
    assert resp.json()['status'] == 'aprovada'


@pytest.mark.asyncio
@pytest.mark.routers
async def test_aprovar_entrada_cc_nao_autorizado(async_client, async_db):
    await _criar_contrato(async_db)
    func1, f1senha = await _criar_usuario(async_db, 'func8')
    func2, f2senha = await _criar_usuario(async_db, 'func9')
    f1token = await _login(async_client, func1.email, f1senha)
    f2token = await _login(async_client, func2.email, f2senha)

    resp = await async_client.post(
        f'{URL}/entrada-cc',
        json={'centro_custo': 'CC01', 'ocupacao_solicitada': 'Funcionario'},
        headers={'Authorization': f'Bearer {f1token}'},
    )
    sol_id = resp.json()['id']

    resp = await async_client.put(
        f'{URL}/{sol_id}/aprovar',
        headers={'Authorization': f'Bearer {f2token}'},
    )

    assert resp.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
@pytest.mark.routers
async def test_aprovar_entrada_cc_subgestor_funcionario(
    async_client, async_db
):
    await _criar_contrato(async_db)
    subg, ssenha = await _criar_usuario(async_db, 'subg3', 'Subgestor')
    await _associar(async_db, subg.id, 'CC01', 'Subgestor')
    func, fsenha = await _criar_usuario(async_db, 'funcA')
    stoken = await _login(async_client, subg.email, ssenha)
    ftoken = await _login(async_client, func.email, fsenha)

    resp = await async_client.post(
        f'{URL}/entrada-cc',
        json={'centro_custo': 'CC01', 'ocupacao_solicitada': 'Funcionario'},
        headers={'Authorization': f'Bearer {ftoken}'},
    )
    sol_id = resp.json()['id']

    resp = await async_client.put(
        f'{URL}/{sol_id}/aprovar',
        headers={'Authorization': f'Bearer {stoken}'},
    )

    assert resp.status_code == HTTPStatus.OK


@pytest.mark.asyncio
@pytest.mark.routers
async def test_aprovar_entrada_cc_subgestor_cargo_maior(
    async_client, async_db
):
    await _criar_contrato(async_db)
    subg, ssenha = await _criar_usuario(async_db, 'subg4', 'Subgestor')
    await _associar(async_db, subg.id, 'CC01', 'Subgestor')
    func, fsenha = await _criar_usuario(async_db, 'funcB')
    stoken = await _login(async_client, subg.email, ssenha)
    ftoken = await _login(async_client, func.email, fsenha)

    resp = await async_client.post(
        f'{URL}/entrada-cc',
        json={'centro_custo': 'CC01', 'ocupacao_solicitada': 'Gestor'},
        headers={'Authorization': f'Bearer {ftoken}'},
    )
    sol_id = resp.json()['id']

    resp = await async_client.put(
        f'{URL}/{sol_id}/aprovar',
        headers={'Authorization': f'Bearer {stoken}'},
    )

    assert resp.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
@pytest.mark.routers
async def test_aprovar_convite(async_client, async_db):
    await _criar_contrato(async_db)
    gestor, gsenha = await _criar_usuario(async_db, 'gest3', 'Gestor')
    await _associar(async_db, gestor.id, 'CC01', 'Gestor')
    convidado, csenha = await _criar_usuario(async_db, 'conv5')
    gtoken = await _login(async_client, gestor.email, gsenha)
    ctoken = await _login(async_client, convidado.email, csenha)

    resp = await async_client.post(
        f'{URL}/convite-cc',
        json={
            'solicitante_id': convidado.id,
            'centro_custo': 'CC01',
            'ocupacao_solicitada': 'Funcionario',
        },
        headers={'Authorization': f'Bearer {gtoken}'},
    )
    sol_id = resp.json()['id']

    resp = await async_client.put(
        f'{URL}/{sol_id}/aprovar',
        headers={'Authorization': f'Bearer {ctoken}'},
    )

    assert resp.status_code == HTTPStatus.OK
    assert resp.json()['status'] == 'aprovada'


@pytest.mark.asyncio
@pytest.mark.routers
async def test_aprovar_convite_outro_usuario(async_client, async_db):
    await _criar_contrato(async_db)
    gestor, gsenha = await _criar_usuario(async_db, 'gest4', 'Gestor')
    await _associar(async_db, gestor.id, 'CC01', 'Gestor')
    convidado, _ = await _criar_usuario(async_db, 'conv6')
    outro, osenha = await _criar_usuario(async_db, 'outro1')
    gtoken = await _login(async_client, gestor.email, gsenha)
    otoken = await _login(async_client, outro.email, osenha)

    resp = await async_client.post(
        f'{URL}/convite-cc',
        json={
            'solicitante_id': convidado.id,
            'centro_custo': 'CC01',
            'ocupacao_solicitada': 'Funcionario',
        },
        headers={'Authorization': f'Bearer {gtoken}'},
    )
    sol_id = resp.json()['id']

    resp = await async_client.put(
        f'{URL}/{sol_id}/aprovar',
        headers={'Authorization': f'Bearer {otoken}'},
    )

    assert resp.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
@pytest.mark.routers
async def test_aprovar_cargo_inicial_admin(
    async_client, async_db, login_teste
):
    func, fsenha = await _criar_usuario(async_db, 'funcC')
    ftoken = await _login(async_client, func.email, fsenha)
    admin_token = login_teste['token']

    resp = await async_client.post(
        f'{URL}/cargo-inicial',
        json={'cargo_solicitado': 'Gestor'},
        headers={'Authorization': f'Bearer {ftoken}'},
    )
    sol_id = resp.json()['id']

    resp = await async_client.put(
        f'{URL}/{sol_id}/aprovar',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    assert resp.status_code == HTTPStatus.OK
    assert resp.json()['status'] == 'aprovada'


@pytest.mark.asyncio
@pytest.mark.routers
async def test_aprovar_cargo_inicial_nao_admin(async_client, async_db):
    func, fsenha = await _criar_usuario(async_db, 'funcD')
    gestor, gsenha = await _criar_usuario(async_db, 'gest5', 'Gestor')
    ftoken = await _login(async_client, func.email, fsenha)
    gtoken = await _login(async_client, gestor.email, gsenha)

    resp = await async_client.post(
        f'{URL}/cargo-inicial',
        json={'cargo_solicitado': 'Gestor'},
        headers={'Authorization': f'Bearer {ftoken}'},
    )
    sol_id = resp.json()['id']

    resp = await async_client.put(
        f'{URL}/{sol_id}/aprovar',
        headers={'Authorization': f'Bearer {gtoken}'},
    )

    assert resp.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
@pytest.mark.routers
async def test_aprovar_ja_aprovada(async_client, async_db, login_teste):
    func, fsenha = await _criar_usuario(async_db, 'funcE')
    ftoken = await _login(async_client, func.email, fsenha)
    admin_token = login_teste['token']

    resp = await async_client.post(
        f'{URL}/cargo-inicial',
        json={'cargo_solicitado': 'Gestor'},
        headers={'Authorization': f'Bearer {ftoken}'},
    )
    sol_id = resp.json()['id']

    await async_client.put(
        f'{URL}/{sol_id}/aprovar',
        headers={'Authorization': f'Bearer {admin_token}'},
    )
    resp = await async_client.put(
        f'{URL}/{sol_id}/aprovar',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    assert resp.status_code == HTTPStatus.BAD_REQUEST


@pytest.mark.asyncio
@pytest.mark.routers
async def test_aprovar_nao_encontrado(async_client, async_db, login_teste):
    admin_token = login_teste['token']

    resp = await async_client.put(
        f'{URL}/9999/aprovar',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    assert resp.status_code == HTTPStatus.NOT_FOUND


# ─── rejeitar ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_rejeitar_entrada_cc(async_client, async_db):
    await _criar_contrato(async_db)
    gestor, gsenha = await _criar_usuario(async_db, 'gest6', 'Gestor')
    await _associar(async_db, gestor.id, 'CC01', 'Gestor')
    func, fsenha = await _criar_usuario(async_db, 'funcF')
    gtoken = await _login(async_client, gestor.email, gsenha)
    ftoken = await _login(async_client, func.email, fsenha)

    resp = await async_client.post(
        f'{URL}/entrada-cc',
        json={'centro_custo': 'CC01', 'ocupacao_solicitada': 'Funcionario'},
        headers={'Authorization': f'Bearer {ftoken}'},
    )
    sol_id = resp.json()['id']

    resp = await async_client.put(
        f'{URL}/{sol_id}/rejeitar',
        headers={'Authorization': f'Bearer {gtoken}'},
    )

    assert resp.status_code == HTTPStatus.OK
    assert resp.json()['status'] == 'rejeitada'


@pytest.mark.asyncio
@pytest.mark.routers
async def test_rejeitar_nao_pendente(async_client, async_db):
    await _criar_contrato(async_db)
    gestor, gsenha = await _criar_usuario(async_db, 'gest7', 'Gestor')
    await _associar(async_db, gestor.id, 'CC01', 'Gestor')
    func, fsenha = await _criar_usuario(async_db, 'funcG')
    gtoken = await _login(async_client, gestor.email, gsenha)
    ftoken = await _login(async_client, func.email, fsenha)

    resp = await async_client.post(
        f'{URL}/entrada-cc',
        json={'centro_custo': 'CC01', 'ocupacao_solicitada': 'Funcionario'},
        headers={'Authorization': f'Bearer {ftoken}'},
    )
    sol_id = resp.json()['id']

    await async_client.put(
        f'{URL}/{sol_id}/rejeitar',
        headers={'Authorization': f'Bearer {gtoken}'},
    )
    resp = await async_client.put(
        f'{URL}/{sol_id}/rejeitar',
        headers={'Authorization': f'Bearer {gtoken}'},
    )

    assert resp.status_code == HTTPStatus.BAD_REQUEST


# ─── cancelar ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_cancelar_solicitacao(async_client, async_db):
    await _criar_contrato(async_db)
    func, fsenha = await _criar_usuario(async_db, 'funcH')
    ftoken = await _login(async_client, func.email, fsenha)

    resp = await async_client.post(
        f'{URL}/entrada-cc',
        json={'centro_custo': 'CC01', 'ocupacao_solicitada': 'Funcionario'},
        headers={'Authorization': f'Bearer {ftoken}'},
    )
    sol_id = resp.json()['id']

    resp = await async_client.delete(
        f'{URL}/{sol_id}',
        headers={'Authorization': f'Bearer {ftoken}'},
    )

    assert resp.status_code == HTTPStatus.OK


@pytest.mark.asyncio
@pytest.mark.routers
async def test_cancelar_outro_usuario(async_client, async_db):
    await _criar_contrato(async_db)
    func, fsenha = await _criar_usuario(async_db, 'funcI')
    outro, osenha = await _criar_usuario(async_db, 'outro2')
    ftoken = await _login(async_client, func.email, fsenha)
    otoken = await _login(async_client, outro.email, osenha)

    resp = await async_client.post(
        f'{URL}/entrada-cc',
        json={'centro_custo': 'CC01', 'ocupacao_solicitada': 'Funcionario'},
        headers={'Authorization': f'Bearer {ftoken}'},
    )
    sol_id = resp.json()['id']

    resp = await async_client.delete(
        f'{URL}/{sol_id}',
        headers={'Authorization': f'Bearer {otoken}'},
    )

    assert resp.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
@pytest.mark.routers
async def test_cancelar_nao_encontrado(async_client, async_db, login_teste):
    admin_token = login_teste['token']

    resp = await async_client.delete(
        f'{URL}/9999',
        headers={'Authorization': f'Bearer {admin_token}'},
    )

    assert resp.status_code == HTTPStatus.NOT_FOUND


# ─── get ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_get_solicitacoes_proprias(async_client, async_db):
    await _criar_contrato(async_db)
    func, fsenha = await _criar_usuario(async_db, 'funcJ')
    ftoken = await _login(async_client, func.email, fsenha)

    await async_client.post(
        f'{URL}/entrada-cc',
        json={'centro_custo': 'CC01', 'ocupacao_solicitada': 'Funcionario'},
        headers={'Authorization': f'Bearer {ftoken}'},
    )

    resp = await async_client.get(
        f'{URL}/', headers={'Authorization': f'Bearer {ftoken}'}
    )

    assert resp.status_code == HTTPStatus.OK
    assert len(resp.json()['solicitacoes']) == 1


@pytest.mark.asyncio
@pytest.mark.routers
async def test_get_gestor_ve_pedidos_do_cc(async_client, async_db):
    await _criar_contrato(async_db)
    gestor, gsenha = await _criar_usuario(async_db, 'gest8', 'Gestor')
    await _associar(async_db, gestor.id, 'CC01', 'Gestor')
    func, fsenha = await _criar_usuario(async_db, 'funcK')
    gtoken = await _login(async_client, gestor.email, gsenha)
    ftoken = await _login(async_client, func.email, fsenha)

    await async_client.post(
        f'{URL}/entrada-cc',
        json={'centro_custo': 'CC01', 'ocupacao_solicitada': 'Subgestor'},
        headers={'Authorization': f'Bearer {ftoken}'},
    )

    resp = await async_client.get(
        f'{URL}/', headers={'Authorization': f'Bearer {gtoken}'}
    )

    solicitacoes = resp.json()['solicitacoes']
    assert any(s['solicitante_id'] == func.id for s in solicitacoes)


@pytest.mark.asyncio
@pytest.mark.routers
async def test_get_subgestor_nao_ve_cargo_maior(async_client, async_db):
    await _criar_contrato(async_db)
    subg, ssenha = await _criar_usuario(async_db, 'subg5', 'Subgestor')
    await _associar(async_db, subg.id, 'CC01', 'Subgestor')
    func, fsenha = await _criar_usuario(async_db, 'funcL')
    stoken = await _login(async_client, subg.email, ssenha)
    ftoken = await _login(async_client, func.email, fsenha)

    await async_client.post(
        f'{URL}/entrada-cc',
        json={'centro_custo': 'CC01', 'ocupacao_solicitada': 'Gestor'},
        headers={'Authorization': f'Bearer {ftoken}'},
    )

    resp = await async_client.get(
        f'{URL}/', headers={'Authorization': f'Bearer {stoken}'}
    )

    solicitacoes = resp.json()['solicitacoes']
    assert not any(s['solicitante_id'] == func.id for s in solicitacoes)


@pytest.mark.asyncio
@pytest.mark.routers
async def test_get_subgestor_ve_pedido_funcionario(async_client, async_db):
    await _criar_contrato(async_db)
    subg, ssenha = await _criar_usuario(async_db, 'subg6', 'Subgestor')
    await _associar(async_db, subg.id, 'CC01', 'Subgestor')
    func, fsenha = await _criar_usuario(async_db, 'funcM')
    stoken = await _login(async_client, subg.email, ssenha)
    ftoken = await _login(async_client, func.email, fsenha)

    await async_client.post(
        f'{URL}/entrada-cc',
        json={'centro_custo': 'CC01', 'ocupacao_solicitada': 'Funcionario'},
        headers={'Authorization': f'Bearer {ftoken}'},
    )

    resp = await async_client.get(
        f'{URL}/', headers={'Authorization': f'Bearer {stoken}'}
    )

    solicitacoes = resp.json()['solicitacoes']
    assert any(s['solicitante_id'] == func.id for s in solicitacoes)
