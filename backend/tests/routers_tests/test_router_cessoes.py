from http import HTTPStatus
from itertools import count

import pytest

from backend.model.associacao_user_contrato import AssociacaoUserContrato
from backend.model.contratos import Contrato
from backend.model.eletronicos import Eletronico
from backend.model.user import User
from backend.security.security import Security

URL = '/cessoes/'

_counter = count(1)


def _n():
    return next(_counter)


async def _criar_usuario(async_db, tipo='Funcionario'):
    n = _n()
    security = Security()
    senha = 'senha123'
    u = User(
        nome=f'CesUser{n}',
        email=f'ces{n}@test.com',
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
    cc = cc or f'CE{_n():03d}'
    c = Contrato(centro_custo=cc, descricao=f'Contrato {cc}')
    async_db.add(c)
    await async_db.flush()
    return c


async def _assoc(async_db, user_id, cc, ocupacao='Gestor'):
    a = AssociacaoUserContrato(
        user_id=user_id, centro_custo=cc, ocupacao=ocupacao
    )
    async_db.add(a)
    await async_db.flush()


async def _criar_eletronico(async_db, cc, status='Interno'):
    n = _n()
    e = Eletronico(
        numero_serie=f'SN-CE{n}',
        numero_patrimonio=f'PAT-CE{n}',
        nome=f'EquipCes{n}',
        tipo='Notbook',
        status=status,
        centro_custo=cc,
    )
    async_db.add(e)
    await async_db.flush()
    await async_db.refresh(e)
    return e


async def _criar_cessao(async_client, token, eletronico_ids, cc_destino):
    return await async_client.post(
        URL,
        json={
            'eletronico_ids': eletronico_ids,
            'responsavel': 'Responsavel',
            'centro_custo_destino': cc_destino,
        },
        headers={'Authorization': f'Bearer {token}'},
    )


# ─── CREATE ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_cessao_admin(async_client, async_db, login_teste):
    c = await _criar_contrato(async_db)
    e = await _criar_eletronico(async_db, c.centro_custo)

    resp = await _criar_cessao(
        async_client, login_teste['token'], [e.id], c.centro_custo
    )

    assert resp.status_code == HTTPStatus.CREATED
    body = resp.json()
    assert body['status'] == 'ativa'
    assert body['total_eletronicos'] == 1
    assert body['eletronicos'][0]['status'] == 'Externo'


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_cessao_gestor_proprio_cc(async_client, async_db):
    c = await _criar_contrato(async_db)
    gestor, gsenha = await _criar_usuario(async_db, 'Gestor')
    await _assoc(async_db, gestor.id, c.centro_custo, 'Gestor')
    e = await _criar_eletronico(async_db, c.centro_custo)
    gtoken = await _login(async_client, gestor.email, gsenha)

    resp = await _criar_cessao(async_client, gtoken, [e.id], c.centro_custo)

    assert resp.status_code == HTTPStatus.CREATED


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_cessao_gestor_cc_alheio_proibido(async_client, async_db):
    c1 = await _criar_contrato(async_db)
    c2 = await _criar_contrato(async_db)
    gestor, gsenha = await _criar_usuario(async_db, 'Gestor')
    await _assoc(async_db, gestor.id, c1.centro_custo, 'Gestor')
    e = await _criar_eletronico(async_db, c2.centro_custo)
    gtoken = await _login(async_client, gestor.email, gsenha)

    resp = await _criar_cessao(async_client, gtoken, [e.id], c1.centro_custo)

    assert resp.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_cessao_funcionario_proibido(async_client, async_db):
    c = await _criar_contrato(async_db)
    func, fsenha = await _criar_usuario(async_db)
    await _assoc(async_db, func.id, c.centro_custo, 'Funcionario')
    e = await _criar_eletronico(async_db, c.centro_custo)
    ftoken = await _login(async_client, func.email, fsenha)

    resp = await _criar_cessao(async_client, ftoken, [e.id], c.centro_custo)

    assert resp.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_cessao_eletronico_ja_externo_retorna_conflict(
    async_client, async_db, login_teste
):
    c = await _criar_contrato(async_db)
    e = await _criar_eletronico(async_db, c.centro_custo, status='Externo')

    resp = await _criar_cessao(
        async_client, login_teste['token'], [e.id], c.centro_custo
    )

    assert resp.status_code == HTTPStatus.CONFLICT


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_cessao_eletronico_nao_encontrado(
    async_client, login_teste
):
    resp = await _criar_cessao(
        async_client, login_teste['token'], [99999], '0001'
    )

    assert resp.status_code == HTTPStatus.NOT_FOUND


# ─── SRP: create() cria cessão + atualiza status + gera vínculos ─────────────
# CessaoService.create() tem três responsabilidades num método.
# Os testes verificam que todos os efeitos ocorrem juntos (e falham juntos).


@pytest.mark.asyncio
@pytest.mark.routers
async def test_criar_cessao_todos_eletronicos_ficam_externo(
    async_client, async_db, login_teste
):
    """
    SRP: create() cria Cessao, atualiza status para Externo e cria
    CessaoEletronico — três responsabilidades num método.
    Todos os efeitos devem ocorrer no mesmo commit.
    """
    c = await _criar_contrato(async_db)
    e1 = await _criar_eletronico(async_db, c.centro_custo)
    e2 = await _criar_eletronico(async_db, c.centro_custo)

    resp = await _criar_cessao(
        async_client, login_teste['token'], [e1.id, e2.id], c.centro_custo
    )

    assert resp.status_code == HTTPStatus.CREATED
    body = resp.json()
    ids_na_resposta = {el['id'] for el in body['eletronicos']}
    assert {e1.id, e2.id} == ids_na_resposta
    for el in body['eletronicos']:
        assert el['status'] == 'Externo'


@pytest.mark.asyncio
@pytest.mark.routers
async def test_criar_cessao_falha_atomicamente_se_um_eletronico_externo(
    async_client, async_db, login_teste
):
    """
    SRP: Como create() acumula responsabilidades, uma falha em qualquer
    etapa deve reverter toda a operação. O eletrônico Interno não deve
    ser alterado quando outro eletrônico bloqueia a criação.
    """
    c = await _criar_contrato(async_db)
    e_interno = await _criar_eletronico(async_db, c.centro_custo, 'Interno')
    e_externo = await _criar_eletronico(async_db, c.centro_custo, 'Externo')

    resp = await _criar_cessao(
        async_client,
        login_teste['token'],
        [e_interno.id, e_externo.id],
        c.centro_custo,
    )

    assert resp.status_code == HTTPStatus.CONFLICT

    await async_db.refresh(e_interno)
    assert e_interno.status == 'Interno', (
        'Eletrônico Interno não deve ser alterado quando a cessão falha'
    )


# ─── GET ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_get_cessoes_admin(async_client, async_db, login_teste):
    c = await _criar_contrato(async_db)
    e = await _criar_eletronico(async_db, c.centro_custo)
    await _criar_cessao(
        async_client, login_teste['token'], [e.id], c.centro_custo
    )

    resp = await async_client.get(
        URL, headers={'Authorization': f'Bearer {login_teste["token"]}'}
    )

    assert resp.status_code == HTTPStatus.OK
    assert len(resp.json()['cessoes']) >= 1


@pytest.mark.asyncio
@pytest.mark.routers
async def test_get_cessao_by_id(async_client, async_db, login_teste):
    c = await _criar_contrato(async_db)
    e = await _criar_eletronico(async_db, c.centro_custo)
    create_resp = await _criar_cessao(
        async_client, login_teste['token'], [e.id], c.centro_custo
    )
    cessao_id = create_resp.json()['id']

    resp = await async_client.get(
        f'{URL}{cessao_id}',
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.OK
    assert resp.json()['id'] == cessao_id


@pytest.mark.asyncio
@pytest.mark.routers
async def test_get_cessao_nao_encontrada(async_client, login_teste):
    resp = await async_client.get(
        f'{URL}99999',
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
@pytest.mark.routers
async def test_get_cessao_sem_permissao_retorna_forbidden(
    async_client, async_db, login_teste
):
    c = await _criar_contrato(async_db)
    e = await _criar_eletronico(async_db, c.centro_custo)
    create_resp = await _criar_cessao(
        async_client, login_teste['token'], [e.id], c.centro_custo
    )
    cessao_id = create_resp.json()['id']
    func, fsenha = await _criar_usuario(async_db)
    ftoken = await _login(async_client, func.email, fsenha)

    resp = await async_client.get(
        f'{URL}{cessao_id}',
        headers={'Authorization': f'Bearer {ftoken}'},
    )

    assert resp.status_code == HTTPStatus.FORBIDDEN


# ─── DEVOLVER ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_devolver_parcial(async_client, async_db, login_teste):
    c = await _criar_contrato(async_db)
    e1 = await _criar_eletronico(async_db, c.centro_custo)
    e2 = await _criar_eletronico(async_db, c.centro_custo)
    e3 = await _criar_eletronico(async_db, c.centro_custo)
    token = login_teste['token']
    create_resp = await _criar_cessao(
        async_client, token, [e1.id, e2.id, e3.id], c.centro_custo
    )
    cessao_id = create_resp.json()['id']

    resp = await async_client.put(
        f'{URL}{cessao_id}/devolver',
        json={'eletronico_ids': [e1.id]},
        headers={'Authorization': f'Bearer {token}'},
    )

    assert resp.status_code == HTTPStatus.OK
    body = resp.json()
    assert body['status'] == 'parcial'
    assert body['total_devolvidos'] == 1
    assert body['total_pendentes'] == 2  # noqa: PLR2004
    assert body['devolucoes'][0]['lote'] == 1


@pytest.mark.asyncio
@pytest.mark.routers
async def test_devolver_segundo_lote_completa_cessao(
    async_client, async_db, login_teste
):
    c = await _criar_contrato(async_db)
    e1 = await _criar_eletronico(async_db, c.centro_custo)
    e2 = await _criar_eletronico(async_db, c.centro_custo)
    token = login_teste['token']
    create_resp = await _criar_cessao(
        async_client, token, [e1.id, e2.id], c.centro_custo
    )
    cessao_id = create_resp.json()['id']

    await async_client.put(
        f'{URL}{cessao_id}/devolver',
        json={'eletronico_ids': [e1.id]},
        headers={'Authorization': f'Bearer {token}'},
    )
    resp = await async_client.put(
        f'{URL}{cessao_id}/devolver',
        json={'eletronico_ids': [e2.id]},
        headers={'Authorization': f'Bearer {token}'},
    )

    body = resp.json()
    assert body['status'] == 'devolvida'
    assert body['total_devolvidos'] == 2  # noqa: PLR2004
    assert body['total_pendentes'] == 0
    lotes = sorted(d['lote'] for d in body['devolucoes'])
    assert lotes == [1, 2]
    assert body['devolvida_em'] is not None


@pytest.mark.asyncio
@pytest.mark.routers
async def test_devolver_item_alheio_a_cessao_retorna_bad_request(
    async_client, async_db, login_teste
):
    c = await _criar_contrato(async_db)
    e = await _criar_eletronico(async_db, c.centro_custo)
    outro = await _criar_eletronico(async_db, c.centro_custo)
    token = login_teste['token']
    create_resp = await _criar_cessao(
        async_client, token, [e.id], c.centro_custo
    )

    resp = await async_client.put(
        f'{URL}{create_resp.json()["id"]}/devolver',
        json={'eletronico_ids': [outro.id]},
        headers={'Authorization': f'Bearer {token}'},
    )

    assert resp.status_code == HTTPStatus.BAD_REQUEST


@pytest.mark.asyncio
@pytest.mark.routers
async def test_devolver_item_ja_devolvido_retorna_bad_request(
    async_client, async_db, login_teste
):
    c = await _criar_contrato(async_db)
    e = await _criar_eletronico(async_db, c.centro_custo)
    token = login_teste['token']
    create_resp = await _criar_cessao(
        async_client, token, [e.id], c.centro_custo
    )
    cessao_id = create_resp.json()['id']

    await async_client.put(
        f'{URL}{cessao_id}/devolver',
        json={'eletronico_ids': [e.id]},
        headers={'Authorization': f'Bearer {token}'},
    )
    resp = await async_client.put(
        f'{URL}{cessao_id}/devolver',
        json={'eletronico_ids': [e.id]},
        headers={'Authorization': f'Bearer {token}'},
    )

    assert resp.status_code == HTTPStatus.BAD_REQUEST


@pytest.mark.asyncio
@pytest.mark.routers
async def test_devolver_membro_do_cc_pode_devolver(async_client, async_db):
    c = await _criar_contrato(async_db)
    gestor, gsenha = await _criar_usuario(async_db, 'Gestor')
    await _assoc(async_db, gestor.id, c.centro_custo, 'Gestor')
    func, fsenha = await _criar_usuario(async_db)
    await _assoc(async_db, func.id, c.centro_custo, 'Funcionario')
    e = await _criar_eletronico(async_db, c.centro_custo)
    gtoken = await _login(async_client, gestor.email, gsenha)
    create_resp = await _criar_cessao(
        async_client, gtoken, [e.id], c.centro_custo
    )
    cessao_id = create_resp.json()['id']
    ftoken = await _login(async_client, func.email, fsenha)

    resp = await async_client.put(
        f'{URL}{cessao_id}/devolver',
        json={'eletronico_ids': [e.id]},
        headers={'Authorization': f'Bearer {ftoken}'},
    )

    assert resp.status_code == HTTPStatus.OK
    assert resp.json()['devolucoes'][0]['devolvida_por_id'] == func.id


@pytest.mark.asyncio
@pytest.mark.routers
async def test_devolver_usuario_fora_do_cc_proibido(async_client, async_db):
    c1 = await _criar_contrato(async_db)
    c2 = await _criar_contrato(async_db)
    gestor, gsenha = await _criar_usuario(async_db, 'Gestor')
    await _assoc(async_db, gestor.id, c1.centro_custo, 'Gestor')
    outsider, osenha = await _criar_usuario(async_db)
    await _assoc(async_db, outsider.id, c2.centro_custo, 'Funcionario')
    e = await _criar_eletronico(async_db, c1.centro_custo)
    gtoken = await _login(async_client, gestor.email, gsenha)
    create_resp = await _criar_cessao(
        async_client, gtoken, [e.id], c1.centro_custo
    )
    otoken = await _login(async_client, outsider.email, osenha)

    resp = await async_client.put(
        f'{URL}{create_resp.json()["id"]}/devolver',
        json={'eletronico_ids': [e.id]},
        headers={'Authorization': f'Bearer {otoken}'},
    )

    assert resp.status_code == HTTPStatus.FORBIDDEN


# ─── DELETE ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_delete_cessao_admin_retorna_eletronico_interno(
    async_client, async_db, login_teste
):
    c = await _criar_contrato(async_db)
    e = await _criar_eletronico(async_db, c.centro_custo)
    token = login_teste['token']
    create_resp = await _criar_cessao(
        async_client, token, [e.id], c.centro_custo
    )
    cessao_id = create_resp.json()['id']

    resp = await async_client.delete(
        f'{URL}{cessao_id}',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert resp.status_code == HTTPStatus.OK
    assert resp.json()['eletronicos'][0]['status'] == 'Interno'


@pytest.mark.asyncio
@pytest.mark.routers
async def test_delete_cessao_gestor_proprio_cc(async_client, async_db):
    c = await _criar_contrato(async_db)
    gestor, gsenha = await _criar_usuario(async_db, 'Gestor')
    await _assoc(async_db, gestor.id, c.centro_custo, 'Gestor')
    e = await _criar_eletronico(async_db, c.centro_custo)
    gtoken = await _login(async_client, gestor.email, gsenha)
    create_resp = await _criar_cessao(
        async_client, gtoken, [e.id], c.centro_custo
    )

    resp = await async_client.delete(
        f'{URL}{create_resp.json()["id"]}',
        headers={'Authorization': f'Bearer {gtoken}'},
    )

    assert resp.status_code == HTTPStatus.OK


@pytest.mark.asyncio
@pytest.mark.routers
async def test_delete_cessao_gestor_cc_alheio_proibido(
    async_client, async_db, login_teste
):
    c1 = await _criar_contrato(async_db)
    c2 = await _criar_contrato(async_db)
    e = await _criar_eletronico(async_db, c1.centro_custo)
    create_resp = await _criar_cessao(
        async_client, login_teste['token'], [e.id], c1.centro_custo
    )
    cessao_id = create_resp.json()['id']
    gestor_outro, gsenha = await _criar_usuario(async_db, 'Gestor')
    await _assoc(async_db, gestor_outro.id, c2.centro_custo, 'Gestor')
    gtoken = await _login(async_client, gestor_outro.email, gsenha)

    resp = await async_client.delete(
        f'{URL}{cessao_id}',
        headers={'Authorization': f'Bearer {gtoken}'},
    )

    assert resp.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
@pytest.mark.routers
async def test_delete_cessao_funcionario_proibido(
    async_client, async_db, login_teste
):
    c = await _criar_contrato(async_db)
    e = await _criar_eletronico(async_db, c.centro_custo)
    create_resp = await _criar_cessao(
        async_client, login_teste['token'], [e.id], c.centro_custo
    )
    func, fsenha = await _criar_usuario(async_db)
    await _assoc(async_db, func.id, c.centro_custo, 'Funcionario')
    ftoken = await _login(async_client, func.email, fsenha)

    resp = await async_client.delete(
        f'{URL}{create_resp.json()["id"]}',
        headers={'Authorization': f'Bearer {ftoken}'},
    )

    assert resp.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
@pytest.mark.routers
async def test_delete_cessao_nao_encontrada(async_client, login_teste):
    resp = await async_client.delete(
        f'{URL}99999',
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.NOT_FOUND


# ─── NOTIFICAÇÕES ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_recebimentos_pendentes_admin_ve_tudo(
    async_client, async_db, login_teste
):
    c = await _criar_contrato(async_db)
    e = await _criar_eletronico(async_db, c.centro_custo)
    token = login_teste['token']
    create_resp = await _criar_cessao(
        async_client, token, [e.id], c.centro_custo
    )
    await async_client.put(
        f'{URL}{create_resp.json()["id"]}/devolver',
        json={'eletronico_ids': [e.id]},
        headers={'Authorization': f'Bearer {token}'},
    )

    resp = await async_client.get(
        f'{URL}recebimentos/pendentes-gestor',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert resp.status_code == HTTPStatus.OK
    assert resp.json()['count'] >= 1


@pytest.mark.asyncio
@pytest.mark.routers
async def test_recebimentos_pendentes_gestor_filtra_por_cc(
    async_client, async_db, login_teste
):
    c1 = await _criar_contrato(async_db)
    c2 = await _criar_contrato(async_db)
    gestor, gsenha = await _criar_usuario(async_db, 'Gestor')
    await _assoc(async_db, gestor.id, c1.centro_custo, 'Gestor')
    e_c1 = await _criar_eletronico(async_db, c1.centro_custo)
    e_c2 = await _criar_eletronico(async_db, c2.centro_custo)
    token = login_teste['token']

    for cc, e in [(c1, e_c1), (c2, e_c2)]:
        cr = await _criar_cessao(async_client, token, [e.id], cc.centro_custo)
        await async_client.put(
            f'{URL}{cr.json()["id"]}/devolver',
            json={'eletronico_ids': [e.id]},
            headers={'Authorization': f'Bearer {token}'},
        )

    gtoken = await _login(async_client, gestor.email, gsenha)
    resp = await async_client.get(
        f'{URL}recebimentos/pendentes-gestor',
        headers={'Authorization': f'Bearer {gtoken}'},
    )

    assert resp.status_code == HTTPStatus.OK
    assert resp.json()['count'] == 1


@pytest.mark.asyncio
@pytest.mark.routers
async def test_recebimentos_pendentes_funcionario_retorna_zero(
    async_client, async_db, login_teste
):
    c = await _criar_contrato(async_db)
    e = await _criar_eletronico(async_db, c.centro_custo)
    func, fsenha = await _criar_usuario(async_db)
    await _assoc(async_db, func.id, c.centro_custo, 'Funcionario')
    token = login_teste['token']
    cr = await _criar_cessao(async_client, token, [e.id], c.centro_custo)
    await async_client.put(
        f'{URL}{cr.json()["id"]}/devolver',
        json={'eletronico_ids': [e.id]},
        headers={'Authorization': f'Bearer {token}'},
    )
    ftoken = await _login(async_client, func.email, fsenha)

    resp = await async_client.get(
        f'{URL}recebimentos/pendentes-gestor',
        headers={'Authorization': f'Bearer {ftoken}'},
    )

    assert resp.status_code == HTTPStatus.OK
    assert resp.json()['count'] == 0


@pytest.mark.asyncio
@pytest.mark.routers
async def test_marcar_recebimentos_vistos_zera_count(
    async_client, async_db, login_teste
):
    c = await _criar_contrato(async_db)
    e = await _criar_eletronico(async_db, c.centro_custo)
    token = login_teste['token']
    cr = await _criar_cessao(async_client, token, [e.id], c.centro_custo)
    await async_client.put(
        f'{URL}{cr.json()["id"]}/devolver',
        json={'eletronico_ids': [e.id]},
        headers={'Authorization': f'Bearer {token}'},
    )

    before = await async_client.get(
        f'{URL}recebimentos/pendentes-gestor',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert before.json()['count'] >= 1

    mark = await async_client.put(
        f'{URL}recebimentos/visto',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert mark.status_code == HTTPStatus.OK
    assert mark.json()['marcadas'] >= 1

    after = await async_client.get(
        f'{URL}recebimentos/pendentes-gestor',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert after.json()['count'] == 0
