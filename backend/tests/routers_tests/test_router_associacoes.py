from http import HTTPStatus
from itertools import count

import pytest

from backend.model.associacao_user_contrato import AssociacaoUserContrato
from backend.model.associacao_user_eletronico import AssociacaoUserEletronico
from backend.model.contratos import Contrato
from backend.model.eletronicos import Eletronico
from backend.model.user import User
from backend.security.security import Security

URL_CONTRATO = '/associacoes/contratos'
URL_ELETRONICO = '/associacoes/eletronicos'

_counter = count(1)


def _n():
    return next(_counter)


async def _criar_usuario(async_db, tipo='Funcionario'):
    n = _n()
    security = Security()
    senha = 'senha123'
    u = User(
        nome=f'AssocUser{n}',
        email=f'assoc{n}@test.com',
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
    cc = cc or f'AS{_n():03d}'
    c = Contrato(centro_custo=cc, descricao=f'Contrato {cc}')
    async_db.add(c)
    await async_db.flush()
    return c


async def _criar_eletronico(async_db, cc):
    n = _n()
    e = Eletronico(
        numero_serie=f'SN-AC{n}',
        numero_patrimonio=f'PAT-AC{n}',
        nome=f'Equipamento{n}',
        tipo='Notbook',
        status='Interno',
        centro_custo=cc,
    )
    async_db.add(e)
    await async_db.flush()
    await async_db.refresh(e)
    return e


async def _assoc_contrato(async_db, user_id, cc, ocupacao='Gestor'):
    a = AssociacaoUserContrato(
        user_id=user_id, centro_custo=cc, ocupacao=ocupacao
    )
    async_db.add(a)
    await async_db.flush()
    return a


async def _assoc_eletronico(async_db, user_id, eletronico_id):
    a = AssociacaoUserEletronico(
        user_id=user_id, eletronico_id=eletronico_id
    )
    async_db.add(a)
    await async_db.flush()
    return a


# ─── AssociacaoUserContrato — GET ────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_get_assoc_contrato_admin_ve_todas(
    async_client, async_db, login_teste
):
    c = await _criar_contrato(async_db)
    u, _ = await _criar_usuario(async_db)
    await _assoc_contrato(async_db, u.id, c.centro_custo, 'Funcionario')

    resp = await async_client.get(
        f'{URL_CONTRATO}/',
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.OK
    assert len(resp.json()['associacoes']) >= 1


@pytest.mark.asyncio
@pytest.mark.routers
async def test_get_assoc_contrato_funcionario_sem_cc_retorna_vazio(
    async_client, async_db
):
    func, fsenha = await _criar_usuario(async_db)
    token = await _login(async_client, func.email, fsenha)

    resp = await async_client.get(
        f'{URL_CONTRATO}/',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert resp.status_code == HTTPStatus.OK
    assert resp.json()['associacoes'] == []


@pytest.mark.asyncio
@pytest.mark.routers
async def test_get_assoc_contrato_gestor_ve_apenas_seu_cc(
    async_client, async_db
):
    c = await _criar_contrato(async_db)
    gestor, gsenha = await _criar_usuario(async_db, 'Gestor')
    await _assoc_contrato(async_db, gestor.id, c.centro_custo, 'Gestor')
    func, _ = await _criar_usuario(async_db)
    await _assoc_contrato(async_db, func.id, c.centro_custo, 'Funcionario')
    gtoken = await _login(async_client, gestor.email, gsenha)

    resp = await async_client.get(
        f'{URL_CONTRATO}/',
        headers={'Authorization': f'Bearer {gtoken}'},
    )

    assert resp.status_code == HTTPStatus.OK
    ccs = {a['centro_custo'] for a in resp.json()['associacoes']}
    assert ccs == {c.centro_custo}


# ─── AssociacaoUserContrato — POST ───────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_assoc_contrato_admin(
    async_client, async_db, login_teste
):
    c = await _criar_contrato(async_db)
    u, _ = await _criar_usuario(async_db)

    resp = await async_client.post(
        f'{URL_CONTRATO}/',
        json={
            'user_id': u.id,
            'centro_custo': c.centro_custo,
            'ocupacao': 'Funcionario',
        },
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.CREATED
    assert resp.json()['ocupacao'] == 'Funcionario'


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_assoc_contrato_gestor_seu_cc(async_client, async_db):
    c = await _criar_contrato(async_db)
    gestor, gsenha = await _criar_usuario(async_db, 'Gestor')
    await _assoc_contrato(async_db, gestor.id, c.centro_custo, 'Gestor')
    u, _ = await _criar_usuario(async_db)
    gtoken = await _login(async_client, gestor.email, gsenha)

    resp = await async_client.post(
        f'{URL_CONTRATO}/',
        json={
            'user_id': u.id,
            'centro_custo': c.centro_custo,
            'ocupacao': 'Subgestor',
        },
        headers={'Authorization': f'Bearer {gtoken}'},
    )

    assert resp.status_code == HTTPStatus.CREATED


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_assoc_contrato_subgestor_pode_adicionar_funcionario(
    async_client, async_db
):
    c = await _criar_contrato(async_db)
    subg, ssenha = await _criar_usuario(async_db, 'Subgestor')
    await _assoc_contrato(async_db, subg.id, c.centro_custo, 'Subgestor')
    u, _ = await _criar_usuario(async_db)
    stoken = await _login(async_client, subg.email, ssenha)

    resp = await async_client.post(
        f'{URL_CONTRATO}/',
        json={
            'user_id': u.id,
            'centro_custo': c.centro_custo,
            'ocupacao': 'Funcionario',
        },
        headers={'Authorization': f'Bearer {stoken}'},
    )

    assert resp.status_code == HTTPStatus.CREATED


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_assoc_contrato_subgestor_nao_pode_adicionar_gestor(
    async_client, async_db
):
    """OCP: regra Subgestor hardcoded — só pode adicionar Funcionario."""
    c = await _criar_contrato(async_db)
    subg, ssenha = await _criar_usuario(async_db, 'Subgestor')
    await _assoc_contrato(async_db, subg.id, c.centro_custo, 'Subgestor')
    u, _ = await _criar_usuario(async_db)
    stoken = await _login(async_client, subg.email, ssenha)

    resp = await async_client.post(
        f'{URL_CONTRATO}/',
        json={
            'user_id': u.id,
            'centro_custo': c.centro_custo,
            'ocupacao': 'Gestor',
        },
        headers={'Authorization': f'Bearer {stoken}'},
    )

    assert resp.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_assoc_contrato_funcionario_proibido(
    async_client, async_db
):
    c = await _criar_contrato(async_db)
    gestor_existente, _ = await _criar_usuario(async_db, 'Gestor')
    await _assoc_contrato(
        async_db, gestor_existente.id, c.centro_custo, 'Gestor'
    )
    func, fsenha = await _criar_usuario(async_db)
    u, _ = await _criar_usuario(async_db)
    ftoken = await _login(async_client, func.email, fsenha)

    resp = await async_client.post(
        f'{URL_CONTRATO}/',
        json={
            'user_id': u.id,
            'centro_custo': c.centro_custo,
            'ocupacao': 'Funcionario',
        },
        headers={'Authorization': f'Bearer {ftoken}'},
    )

    assert resp.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_assoc_contrato_duplicada_retorna_conflict(
    async_client, async_db, login_teste
):
    c = await _criar_contrato(async_db)
    u, _ = await _criar_usuario(async_db)
    payload = {
        'user_id': u.id,
        'centro_custo': c.centro_custo,
        'ocupacao': 'Funcionario',
    }

    await async_client.post(
        f'{URL_CONTRATO}/', json=payload,
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    resp = await async_client.post(
        f'{URL_CONTRATO}/', json=payload,
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.CONFLICT


# ─── AssociacaoUserContrato — PUT ────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_update_assoc_contrato_admin(
    async_client, async_db, login_teste
):
    c = await _criar_contrato(async_db)
    u, _ = await _criar_usuario(async_db)
    await _assoc_contrato(async_db, u.id, c.centro_custo, 'Funcionario')

    resp = await async_client.put(
        f'{URL_CONTRATO}/{u.id}/{c.centro_custo}',
        json={
            'user_id': u.id,
            'centro_custo': c.centro_custo,
            'ocupacao': 'Subgestor',
        },
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.OK
    assert resp.json()['ocupacao'] == 'Subgestor'


@pytest.mark.asyncio
@pytest.mark.routers
async def test_update_assoc_contrato_gestor(async_client, async_db):
    c = await _criar_contrato(async_db)
    gestor, gsenha = await _criar_usuario(async_db, 'Gestor')
    await _assoc_contrato(async_db, gestor.id, c.centro_custo, 'Gestor')
    u, _ = await _criar_usuario(async_db)
    await _assoc_contrato(async_db, u.id, c.centro_custo, 'Funcionario')
    gtoken = await _login(async_client, gestor.email, gsenha)

    resp = await async_client.put(
        f'{URL_CONTRATO}/{u.id}/{c.centro_custo}',
        json={
            'user_id': u.id,
            'centro_custo': c.centro_custo,
            'ocupacao': 'Subgestor',
        },
        headers={'Authorization': f'Bearer {gtoken}'},
    )

    assert resp.status_code == HTTPStatus.OK
    assert resp.json()['ocupacao'] == 'Subgestor'


@pytest.mark.asyncio
@pytest.mark.routers
async def test_update_assoc_gestor_nao_pode_rebaixar_outro_gestor(
    async_client, async_db
):
    c = await _criar_contrato(async_db)
    gestor1, g1senha = await _criar_usuario(async_db, 'Gestor')
    await _assoc_contrato(async_db, gestor1.id, c.centro_custo, 'Gestor')
    gestor2, _ = await _criar_usuario(async_db, 'Gestor')
    await _assoc_contrato(async_db, gestor2.id, c.centro_custo, 'Gestor')
    g1token = await _login(async_client, gestor1.email, g1senha)

    resp = await async_client.put(
        f'{URL_CONTRATO}/{gestor2.id}/{c.centro_custo}',
        json={
            'user_id': gestor2.id,
            'centro_custo': c.centro_custo,
            'ocupacao': 'Funcionario',
        },
        headers={'Authorization': f'Bearer {g1token}'},
    )

    assert resp.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
@pytest.mark.routers
async def test_update_assoc_admin_pode_rebaixar_gestor(
    async_client, async_db, login_teste
):
    c = await _criar_contrato(async_db)
    gestor, _ = await _criar_usuario(async_db, 'Gestor')
    await _assoc_contrato(async_db, gestor.id, c.centro_custo, 'Gestor')

    resp = await async_client.put(
        f'{URL_CONTRATO}/{gestor.id}/{c.centro_custo}',
        json={
            'user_id': gestor.id,
            'centro_custo': c.centro_custo,
            'ocupacao': 'Funcionario',
        },
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.OK
    assert resp.json()['ocupacao'] == 'Funcionario'


@pytest.mark.asyncio
@pytest.mark.routers
async def test_update_assoc_contrato_subgestor_proibido(
    async_client, async_db
):
    c = await _criar_contrato(async_db)
    subg, ssenha = await _criar_usuario(async_db, 'Subgestor')
    await _assoc_contrato(async_db, subg.id, c.centro_custo, 'Subgestor')
    u, _ = await _criar_usuario(async_db)
    await _assoc_contrato(async_db, u.id, c.centro_custo, 'Funcionario')
    stoken = await _login(async_client, subg.email, ssenha)

    resp = await async_client.put(
        f'{URL_CONTRATO}/{u.id}/{c.centro_custo}',
        json={
            'user_id': u.id,
            'centro_custo': c.centro_custo,
            'ocupacao': 'Funcionario',
        },
        headers={'Authorization': f'Bearer {stoken}'},
    )

    assert resp.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
@pytest.mark.routers
async def test_update_assoc_contrato_nao_encontrado(
    async_client, async_db, login_teste
):
    c = await _criar_contrato(async_db)

    resp = await async_client.put(
        f'{URL_CONTRATO}/9999/{c.centro_custo}',
        json={
            'user_id': 9999,
            'centro_custo': c.centro_custo,
            'ocupacao': 'Funcionario',
        },
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.NOT_FOUND


# ─── AssociacaoUserContrato — DELETE ─────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_delete_assoc_contrato_admin(
    async_client, async_db, login_teste
):
    c = await _criar_contrato(async_db)
    u, _ = await _criar_usuario(async_db)
    await _assoc_contrato(async_db, u.id, c.centro_custo, 'Funcionario')

    resp = await async_client.delete(
        f'{URL_CONTRATO}/{u.id}/{c.centro_custo}',
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.OK
    assert resp.json()['user_id'] == u.id


@pytest.mark.asyncio
@pytest.mark.routers
async def test_delete_assoc_contrato_gestor(async_client, async_db):
    c = await _criar_contrato(async_db)
    gestor, gsenha = await _criar_usuario(async_db, 'Gestor')
    await _assoc_contrato(async_db, gestor.id, c.centro_custo, 'Gestor')
    u, _ = await _criar_usuario(async_db)
    await _assoc_contrato(async_db, u.id, c.centro_custo, 'Funcionario')
    gtoken = await _login(async_client, gestor.email, gsenha)

    resp = await async_client.delete(
        f'{URL_CONTRATO}/{u.id}/{c.centro_custo}',
        headers={'Authorization': f'Bearer {gtoken}'},
    )

    assert resp.status_code == HTTPStatus.OK


@pytest.mark.asyncio
@pytest.mark.routers
async def test_delete_assoc_contrato_subgestor_pode_remover_funcionario(
    async_client, async_db
):
    c = await _criar_contrato(async_db)
    subg, ssenha = await _criar_usuario(async_db, 'Subgestor')
    await _assoc_contrato(async_db, subg.id, c.centro_custo, 'Subgestor')
    u, _ = await _criar_usuario(async_db)
    await _assoc_contrato(async_db, u.id, c.centro_custo, 'Funcionario')
    stoken = await _login(async_client, subg.email, ssenha)

    resp = await async_client.delete(
        f'{URL_CONTRATO}/{u.id}/{c.centro_custo}',
        headers={'Authorization': f'Bearer {stoken}'},
    )

    assert resp.status_code == HTTPStatus.OK


@pytest.mark.asyncio
@pytest.mark.routers
async def test_delete_assoc_contrato_subgestor_nao_pode_remover_gestor(
    async_client, async_db
):
    c = await _criar_contrato(async_db)
    subg, ssenha = await _criar_usuario(async_db, 'Subgestor')
    await _assoc_contrato(async_db, subg.id, c.centro_custo, 'Subgestor')
    gestor2, _ = await _criar_usuario(async_db, 'Gestor')
    await _assoc_contrato(async_db, gestor2.id, c.centro_custo, 'Gestor')
    stoken = await _login(async_client, subg.email, ssenha)

    resp = await async_client.delete(
        f'{URL_CONTRATO}/{gestor2.id}/{c.centro_custo}',
        headers={'Authorization': f'Bearer {stoken}'},
    )

    assert resp.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
@pytest.mark.routers
async def test_delete_assoc_contrato_nao_encontrado(
    async_client, async_db, login_teste
):
    c = await _criar_contrato(async_db)

    resp = await async_client.delete(
        f'{URL_CONTRATO}/9999/{c.centro_custo}',
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.NOT_FOUND


# ─── AssociacaoUserEletronico — GET ──────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_get_assoc_eletronico_admin_ve_todas(
    async_client, async_db, login_teste
):
    c = await _criar_contrato(async_db)
    e = await _criar_eletronico(async_db, c.centro_custo)
    u, _ = await _criar_usuario(async_db)
    await _assoc_eletronico(async_db, u.id, e.id)

    resp = await async_client.get(
        f'{URL_ELETRONICO}/',
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.OK
    assert len(resp.json()['associacoes']) >= 1


@pytest.mark.asyncio
@pytest.mark.routers
async def test_get_assoc_eletronico_funcionario_ve_apenas_proprias(
    async_client, async_db
):
    c = await _criar_contrato(async_db)
    func, fsenha = await _criar_usuario(async_db)
    await _assoc_contrato(async_db, func.id, c.centro_custo, 'Funcionario')
    e = await _criar_eletronico(async_db, c.centro_custo)
    await _assoc_eletronico(async_db, func.id, e.id)
    outro, _ = await _criar_usuario(async_db)
    e2 = await _criar_eletronico(async_db, c.centro_custo)
    await _assoc_eletronico(async_db, outro.id, e2.id)
    ftoken = await _login(async_client, func.email, fsenha)

    resp = await async_client.get(
        f'{URL_ELETRONICO}/',
        headers={'Authorization': f'Bearer {ftoken}'},
    )

    assert resp.status_code == HTTPStatus.OK
    user_ids = {a['user_id'] for a in resp.json()['associacoes']}
    assert user_ids == {func.id}


@pytest.mark.asyncio
@pytest.mark.routers
async def test_get_assoc_eletronico_gestor_ve_do_seu_cc(
    async_client, async_db
):
    c = await _criar_contrato(async_db)
    gestor, gsenha = await _criar_usuario(async_db, 'Gestor')
    await _assoc_contrato(async_db, gestor.id, c.centro_custo, 'Gestor')
    e = await _criar_eletronico(async_db, c.centro_custo)
    u, _ = await _criar_usuario(async_db)
    await _assoc_eletronico(async_db, u.id, e.id)
    gtoken = await _login(async_client, gestor.email, gsenha)

    resp = await async_client.get(
        f'{URL_ELETRONICO}/',
        headers={'Authorization': f'Bearer {gtoken}'},
    )

    assert resp.status_code == HTTPStatus.OK
    assert any(a['eletronico_id'] == e.id for a in resp.json()['associacoes'])


# ─── AssociacaoUserEletronico — POST ─────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_assoc_eletronico_admin(
    async_client, async_db, login_teste
):
    c = await _criar_contrato(async_db)
    e = await _criar_eletronico(async_db, c.centro_custo)
    u, _ = await _criar_usuario(async_db)

    resp = await async_client.post(
        f'{URL_ELETRONICO}/',
        json={'user_id': u.id, 'eletronico_id': e.id},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.CREATED
    assert resp.json()['eletronico_id'] == e.id


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_assoc_eletronico_gestor(async_client, async_db):
    c = await _criar_contrato(async_db)
    gestor, gsenha = await _criar_usuario(async_db, 'Gestor')
    await _assoc_contrato(async_db, gestor.id, c.centro_custo, 'Gestor')
    e = await _criar_eletronico(async_db, c.centro_custo)
    u, _ = await _criar_usuario(async_db)
    gtoken = await _login(async_client, gestor.email, gsenha)

    resp = await async_client.post(
        f'{URL_ELETRONICO}/',
        json={'user_id': u.id, 'eletronico_id': e.id},
        headers={'Authorization': f'Bearer {gtoken}'},
    )

    assert resp.status_code == HTTPStatus.CREATED


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_assoc_eletronico_funcionario_pode_associar_si_mesmo(
    async_client, async_db
):
    c = await _criar_contrato(async_db)
    func, fsenha = await _criar_usuario(async_db)
    await _assoc_contrato(async_db, func.id, c.centro_custo, 'Funcionario')
    e = await _criar_eletronico(async_db, c.centro_custo)
    ftoken = await _login(async_client, func.email, fsenha)

    resp = await async_client.post(
        f'{URL_ELETRONICO}/',
        json={'user_id': func.id, 'eletronico_id': e.id},
        headers={'Authorization': f'Bearer {ftoken}'},
    )

    assert resp.status_code == HTTPStatus.CREATED


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_assoc_eletronico_funcionario_nao_pode_associar_outro(
    async_client, async_db
):
    c = await _criar_contrato(async_db)
    func, fsenha = await _criar_usuario(async_db)
    await _assoc_contrato(async_db, func.id, c.centro_custo, 'Funcionario')
    outro, _ = await _criar_usuario(async_db)
    e = await _criar_eletronico(async_db, c.centro_custo)
    ftoken = await _login(async_client, func.email, fsenha)

    resp = await async_client.post(
        f'{URL_ELETRONICO}/',
        json={'user_id': outro.id, 'eletronico_id': e.id},
        headers={'Authorization': f'Bearer {ftoken}'},
    )

    assert resp.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_assoc_eletronico_nao_encontrado(
    async_client, async_db, login_teste
):
    u, _ = await _criar_usuario(async_db)

    resp = await async_client.post(
        f'{URL_ELETRONICO}/',
        json={'user_id': u.id, 'eletronico_id': 9999},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_assoc_eletronico_duplicada_retorna_conflict(
    async_client, async_db, login_teste
):
    c = await _criar_contrato(async_db)
    e = await _criar_eletronico(async_db, c.centro_custo)
    u, _ = await _criar_usuario(async_db)
    payload = {'user_id': u.id, 'eletronico_id': e.id}

    await async_client.post(
        f'{URL_ELETRONICO}/', json=payload,
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    resp = await async_client.post(
        f'{URL_ELETRONICO}/', json=payload,
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.CONFLICT


# ─── AssociacaoUserEletronico — DELETE ───────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_delete_assoc_eletronico_admin(
    async_client, async_db, login_teste
):
    c = await _criar_contrato(async_db)
    e = await _criar_eletronico(async_db, c.centro_custo)
    u, _ = await _criar_usuario(async_db)
    await _assoc_eletronico(async_db, u.id, e.id)

    resp = await async_client.delete(
        f'{URL_ELETRONICO}/{u.id}/{e.id}',
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.OK
    assert resp.json()['eletronico_id'] == e.id


@pytest.mark.asyncio
@pytest.mark.routers
async def test_delete_assoc_eletronico_gestor(async_client, async_db):
    c = await _criar_contrato(async_db)
    gestor, gsenha = await _criar_usuario(async_db, 'Gestor')
    await _assoc_contrato(async_db, gestor.id, c.centro_custo, 'Gestor')
    e = await _criar_eletronico(async_db, c.centro_custo)
    u, _ = await _criar_usuario(async_db)
    await _assoc_eletronico(async_db, u.id, e.id)
    gtoken = await _login(async_client, gestor.email, gsenha)

    resp = await async_client.delete(
        f'{URL_ELETRONICO}/{u.id}/{e.id}',
        headers={'Authorization': f'Bearer {gtoken}'},
    )

    assert resp.status_code == HTTPStatus.OK


@pytest.mark.asyncio
@pytest.mark.routers
async def test_delete_assoc_eletronico_funcionario_pode_remover_propria(
    async_client, async_db
):
    c = await _criar_contrato(async_db)
    func, fsenha = await _criar_usuario(async_db)
    await _assoc_contrato(async_db, func.id, c.centro_custo, 'Funcionario')
    e = await _criar_eletronico(async_db, c.centro_custo)
    await _assoc_eletronico(async_db, func.id, e.id)
    ftoken = await _login(async_client, func.email, fsenha)

    resp = await async_client.delete(
        f'{URL_ELETRONICO}/{func.id}/{e.id}',
        headers={'Authorization': f'Bearer {ftoken}'},
    )

    assert resp.status_code == HTTPStatus.OK


@pytest.mark.asyncio
@pytest.mark.routers
async def test_delete_assoc_eletronico_funcionario_nao_pode_remover_alheia(
    async_client, async_db
):
    c = await _criar_contrato(async_db)
    func, fsenha = await _criar_usuario(async_db)
    await _assoc_contrato(async_db, func.id, c.centro_custo, 'Funcionario')
    outro, _ = await _criar_usuario(async_db)
    e = await _criar_eletronico(async_db, c.centro_custo)
    await _assoc_eletronico(async_db, outro.id, e.id)
    ftoken = await _login(async_client, func.email, fsenha)

    resp = await async_client.delete(
        f'{URL_ELETRONICO}/{outro.id}/{e.id}',
        headers={'Authorization': f'Bearer {ftoken}'},
    )

    assert resp.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
@pytest.mark.routers
async def test_delete_assoc_eletronico_nao_encontrado(
    async_client, async_db, login_teste
):
    c = await _criar_contrato(async_db)
    e = await _criar_eletronico(async_db, c.centro_custo)

    resp = await async_client.delete(
        f'{URL_ELETRONICO}/9999/{e.id}',
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.NOT_FOUND


# ─── LSP: AssociacaoEletronico não implementa update ─────────────────────────
# AssociacaoUserContratoService tem create/read/update/delete.
# AssociacaoUserEletronicoService tem apenas create/read/delete.
# Se os dois representam o mesmo conceito (associação), deveriam ter
# a mesma interface (LSP). Os testes documentam a assimetria.


@pytest.mark.asyncio
@pytest.mark.routers
async def test_assoc_contrato_tem_endpoint_put(
    async_client, async_db, login_teste
):
    """LSP: AssociacaoContrato expõe PUT — interface completa."""
    c = await _criar_contrato(async_db)
    u, _ = await _criar_usuario(async_db)
    await _assoc_contrato(async_db, u.id, c.centro_custo, 'Funcionario')

    resp = await async_client.put(
        f'{URL_CONTRATO}/{u.id}/{c.centro_custo}',
        json={
            'user_id': u.id,
            'centro_custo': c.centro_custo,
            'ocupacao': 'Subgestor',
        },
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.OK


@pytest.mark.asyncio
@pytest.mark.routers
async def test_assoc_eletronico_nao_tem_endpoint_put(
    async_client, async_db, login_teste
):
    """
    LSP: AssociacaoEletronico NÃO implementa update — interface assimétrica
    em relação a AssociacaoContrato. Ambos representam o conceito de
    associação mas não são substituíveis.
    """
    c = await _criar_contrato(async_db)
    e = await _criar_eletronico(async_db, c.centro_custo)
    u, _ = await _criar_usuario(async_db)
    await _assoc_eletronico(async_db, u.id, e.id)

    resp = await async_client.put(
        f'{URL_ELETRONICO}/{u.id}/{e.id}',
        json={'user_id': u.id, 'eletronico_id': e.id},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code in {
        HTTPStatus.METHOD_NOT_ALLOWED,
        HTTPStatus.NOT_FOUND,
    }


@pytest.mark.asyncio
@pytest.mark.routers
async def test_ambas_associacoes_rejeitam_recurso_inexistente_com_404(
    async_client, async_db, login_teste
):
    """
    LSP (corrigido): Ambos os serviços validam explicitamente a existência
    do recurso referenciado e retornam 404 de forma consistente.
    AssociacaoUserContratoService valida o CC;
    AssociacaoUserEletronicoService valida o eletrônico.
    """
    token = login_teste['token']
    user, _ = await _criar_usuario(async_db)

    # CC inexistente — serviço valida → 404
    contrato_resp = await async_client.post(
        f'{URL_CONTRATO}/',
        json={
            'user_id': user.id,
            'centro_custo': 'CCXXINVALIDO',
            'ocupacao': 'Funcionario',
        },
        headers={'Authorization': f'Bearer {token}'},
    )
    # Eletrônico inexistente — serviço valida → 404
    eletronico_resp = await async_client.post(
        f'{URL_ELETRONICO}/',
        json={'user_id': user.id, 'eletronico_id': 999998},
        headers={'Authorization': f'Bearer {token}'},
    )

    assert contrato_resp.status_code == HTTPStatus.NOT_FOUND
    assert eletronico_resp.status_code == HTTPStatus.NOT_FOUND
    assert contrato_resp.status_code == eletronico_resp.status_code
