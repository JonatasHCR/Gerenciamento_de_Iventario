from http import HTTPStatus
from itertools import count

import pytest

from backend.model.associacao_user_contrato import AssociacaoUserContrato
from backend.model.contratos import Contrato
from backend.model.eletronicos import Eletronico
from backend.model.user import User
from backend.security.security import Security

URL_CESSAO = '/cessoes/'

_counter = count(1)


def _n():
    return next(_counter)


# ─── Helpers ────────────────────────────────────────────────────────────────


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
    cc = cc or f'C{_n():03d}'
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
    return a


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


# ─── CREATE ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_cessao_admin(async_client, async_db, login_teste):
    c = await _criar_contrato(async_db)
    e = await _criar_eletronico(async_db, c.centro_custo)

    resp = await async_client.post(
        URL_CESSAO,
        json={
            'eletronico_ids': [e.id],
            'responsavel': 'Fulano',
            'centro_custo_destino': c.centro_custo,
        },
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.CREATED
    body = resp.json()
    assert body['status'] == 'ativa'
    assert body['total_eletronicos'] == 1
    assert body['total_pendentes'] == 1
    assert body['total_devolvidos'] == 0
    assert body['eletronicos'][0]['status'] == 'Externo'


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_cessao_gestor_proprio_cc(async_client, async_db):
    c = await _criar_contrato(async_db)
    gestor, gsenha = await _criar_usuario(async_db, 'Gestor')
    await _assoc(async_db, gestor.id, c.centro_custo, 'Gestor')
    e = await _criar_eletronico(async_db, c.centro_custo)
    token = await _login(async_client, gestor.email, gsenha)

    resp = await async_client.post(
        URL_CESSAO,
        json={
            'eletronico_ids': [e.id],
            'responsavel': 'Fulano',
            'centro_custo_destino': c.centro_custo,
        },
        headers={'Authorization': f'Bearer {token}'},
    )

    assert resp.status_code == HTTPStatus.CREATED


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_cessao_gestor_cc_alheio(async_client, async_db):
    c1 = await _criar_contrato(async_db)
    c2 = await _criar_contrato(async_db)
    gestor, gsenha = await _criar_usuario(async_db, 'Gestor')
    # Gestor apenas no c1, mas tenta ceder eletrônico do c2
    await _assoc(async_db, gestor.id, c1.centro_custo, 'Gestor')
    e = await _criar_eletronico(async_db, c2.centro_custo)
    token = await _login(async_client, gestor.email, gsenha)

    resp = await async_client.post(
        URL_CESSAO,
        json={
            'eletronico_ids': [e.id],
            'responsavel': 'Fulano',
            'centro_custo_destino': c1.centro_custo,
        },
        headers={'Authorization': f'Bearer {token}'},
    )

    assert resp.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_cessao_funcionario_proibido(async_client, async_db):
    c = await _criar_contrato(async_db)
    func, fsenha = await _criar_usuario(async_db)
    await _assoc(async_db, func.id, c.centro_custo, 'Funcionario')
    e = await _criar_eletronico(async_db, c.centro_custo)
    token = await _login(async_client, func.email, fsenha)

    resp = await async_client.post(
        URL_CESSAO,
        json={
            'eletronico_ids': [e.id],
            'responsavel': 'Fulano',
            'centro_custo_destino': c.centro_custo,
        },
        headers={'Authorization': f'Bearer {token}'},
    )

    assert resp.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_cessao_eletronico_ja_externo(
    async_client, async_db, login_teste
):
    c = await _criar_contrato(async_db)
    e = await _criar_eletronico(async_db, c.centro_custo, status='Externo')

    resp = await async_client.post(
        URL_CESSAO,
        json={
            'eletronico_ids': [e.id],
            'responsavel': 'Fulano',
            'centro_custo_destino': c.centro_custo,
        },
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.CONFLICT


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_cessao_eletronico_nao_encontrado(
    async_client, login_teste
):
    resp = await async_client.post(
        URL_CESSAO,
        json={
            'eletronico_ids': [99999],
            'responsavel': 'Fulano',
            'centro_custo_destino': '0001',
        },
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.NOT_FOUND


# ─── GET ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_get_cessoes_admin(async_client, async_db, login_teste):
    c = await _criar_contrato(async_db)
    e = await _criar_eletronico(async_db, c.centro_custo)
    await async_client.post(
        URL_CESSAO,
        json={
            'eletronico_ids': [e.id],
            'responsavel': 'X',
            'centro_custo_destino': c.centro_custo,
        },
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    resp = await async_client.get(
        URL_CESSAO,
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.OK
    assert len(resp.json()['cessoes']) >= 1


@pytest.mark.asyncio
@pytest.mark.routers
async def test_get_cessao_by_id(async_client, async_db, login_teste):
    c = await _criar_contrato(async_db)
    e = await _criar_eletronico(async_db, c.centro_custo)
    create_resp = await async_client.post(
        URL_CESSAO,
        json={
            'eletronico_ids': [e.id],
            'responsavel': 'X',
            'centro_custo_destino': c.centro_custo,
        },
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    cessao_id = create_resp.json()['id']

    resp = await async_client.get(
        f'{URL_CESSAO}{cessao_id}',
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.OK
    assert resp.json()['id'] == cessao_id


@pytest.mark.asyncio
@pytest.mark.routers
async def test_get_cessao_nao_encontrada(async_client, login_teste):
    resp = await async_client.get(
        f'{URL_CESSAO}99999',
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    assert resp.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
@pytest.mark.routers
async def test_get_cessao_sem_permissao(async_client, async_db, login_teste):
    """Funcionário que não criou nem é gestor de nenhum CC envolvido
    recebe 403 ao ler cessão alheia."""
    c = await _criar_contrato(async_db)
    e = await _criar_eletronico(async_db, c.centro_custo)
    create_resp = await async_client.post(
        URL_CESSAO,
        json={
            'eletronico_ids': [e.id],
            'responsavel': 'X',
            'centro_custo_destino': c.centro_custo,
        },
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    cessao_id = create_resp.json()['id']
    func, fsenha = await _criar_usuario(async_db)
    token = await _login(async_client, func.email, fsenha)

    resp = await async_client.get(
        f'{URL_CESSAO}{cessao_id}',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert resp.status_code == HTTPStatus.FORBIDDEN


# ─── DEVOLVER (parcial + total) ────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_devolver_parcial(async_client, async_db, login_teste):
    c = await _criar_contrato(async_db)
    e1 = await _criar_eletronico(async_db, c.centro_custo)
    e2 = await _criar_eletronico(async_db, c.centro_custo)
    e3 = await _criar_eletronico(async_db, c.centro_custo)
    create_resp = await async_client.post(
        URL_CESSAO,
        json={
            'eletronico_ids': [e1.id, e2.id, e3.id],
            'responsavel': 'X',
            'centro_custo_destino': c.centro_custo,
        },
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    cessao_id = create_resp.json()['id']

    # devolve só 1
    resp = await async_client.put(
        f'{URL_CESSAO}{cessao_id}/devolver',
        json={'eletronico_ids': [e1.id]},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.OK
    body = resp.json()
    assert body['status'] == 'parcial'
    assert body['total_devolvidos'] == 1
    assert body['total_pendentes'] == 2  # noqa: PLR2004
    assert len(body['devolucoes']) == 1
    assert body['devolucoes'][0]['lote'] == 1


@pytest.mark.asyncio
@pytest.mark.routers
async def test_devolver_segundo_lote_e_completar(
    async_client, async_db, login_teste
):
    c = await _criar_contrato(async_db)
    e1 = await _criar_eletronico(async_db, c.centro_custo)
    e2 = await _criar_eletronico(async_db, c.centro_custo)
    create_resp = await async_client.post(
        URL_CESSAO,
        json={
            'eletronico_ids': [e1.id, e2.id],
            'responsavel': 'X',
            'centro_custo_destino': c.centro_custo,
        },
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    cessao_id = create_resp.json()['id']

    await async_client.put(
        f'{URL_CESSAO}{cessao_id}/devolver',
        json={'eletronico_ids': [e1.id]},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    resp = await async_client.put(
        f'{URL_CESSAO}{cessao_id}/devolver',
        json={'eletronico_ids': [e2.id]},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
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
async def test_devolver_item_alheio_a_cessao(
    async_client, async_db, login_teste
):
    c = await _criar_contrato(async_db)
    e = await _criar_eletronico(async_db, c.centro_custo)
    outro_e = await _criar_eletronico(async_db, c.centro_custo)
    create_resp = await async_client.post(
        URL_CESSAO,
        json={
            'eletronico_ids': [e.id],
            'responsavel': 'X',
            'centro_custo_destino': c.centro_custo,
        },
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    resp = await async_client.put(
        f'{URL_CESSAO}{create_resp.json()["id"]}/devolver',
        json={'eletronico_ids': [outro_e.id]},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.BAD_REQUEST


@pytest.mark.asyncio
@pytest.mark.routers
async def test_devolver_item_ja_devolvido(
    async_client, async_db, login_teste
):
    c = await _criar_contrato(async_db)
    e = await _criar_eletronico(async_db, c.centro_custo)
    create_resp = await async_client.post(
        URL_CESSAO,
        json={
            'eletronico_ids': [e.id],
            'responsavel': 'X',
            'centro_custo_destino': c.centro_custo,
        },
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    cessao_id = create_resp.json()['id']
    await async_client.put(
        f'{URL_CESSAO}{cessao_id}/devolver',
        json={'eletronico_ids': [e.id]},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    # tenta devolver de novo → 400 (cessão já devolvida)
    resp = await async_client.put(
        f'{URL_CESSAO}{cessao_id}/devolver',
        json={'eletronico_ids': [e.id]},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.BAD_REQUEST


@pytest.mark.asyncio
@pytest.mark.routers
async def test_devolver_funcionario_do_cc_permitido(async_client, async_db):
    """Qualquer membro do CC (qualquer ocupação) pode devolver."""
    c = await _criar_contrato(async_db)
    gestor, gsenha = await _criar_usuario(async_db, 'Gestor')
    await _assoc(async_db, gestor.id, c.centro_custo, 'Gestor')
    func, fsenha = await _criar_usuario(async_db)
    await _assoc(async_db, func.id, c.centro_custo, 'Funcionario')
    e = await _criar_eletronico(async_db, c.centro_custo)
    gtoken = await _login(async_client, gestor.email, gsenha)
    create_resp = await async_client.post(
        URL_CESSAO,
        json={
            'eletronico_ids': [e.id],
            'responsavel': 'X',
            'centro_custo_destino': c.centro_custo,
        },
        headers={'Authorization': f'Bearer {gtoken}'},
    )
    cessao_id = create_resp.json()['id']
    ftoken = await _login(async_client, func.email, fsenha)

    resp = await async_client.put(
        f'{URL_CESSAO}{cessao_id}/devolver',
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
    outro, osenha = await _criar_usuario(async_db, 'Funcionario')
    await _assoc(async_db, outro.id, c2.centro_custo, 'Funcionario')
    e = await _criar_eletronico(async_db, c1.centro_custo)
    gtoken = await _login(async_client, gestor.email, gsenha)
    create_resp = await async_client.post(
        URL_CESSAO,
        json={
            'eletronico_ids': [e.id],
            'responsavel': 'X',
            'centro_custo_destino': c1.centro_custo,
        },
        headers={'Authorization': f'Bearer {gtoken}'},
    )
    otoken = await _login(async_client, outro.email, osenha)

    resp = await async_client.put(
        f'{URL_CESSAO}{create_resp.json()["id"]}/devolver',
        json={'eletronico_ids': [e.id]},
        headers={'Authorization': f'Bearer {otoken}'},
    )

    assert resp.status_code == HTTPStatus.FORBIDDEN


# ─── DELETE ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_delete_cessao_admin(async_client, async_db, login_teste):
    c = await _criar_contrato(async_db)
    e = await _criar_eletronico(async_db, c.centro_custo)
    create_resp = await async_client.post(
        URL_CESSAO,
        json={
            'eletronico_ids': [e.id],
            'responsavel': 'X',
            'centro_custo_destino': c.centro_custo,
        },
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    cessao_id = create_resp.json()['id']

    resp = await async_client.delete(
        f'{URL_CESSAO}{cessao_id}',
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.OK
    # eletrônico volta a interno
    assert resp.json()['eletronicos'][0]['status'] == 'Interno'


@pytest.mark.asyncio
@pytest.mark.routers
async def test_delete_cessao_gestor_proprio_cc(async_client, async_db):
    c = await _criar_contrato(async_db)
    gestor, gsenha = await _criar_usuario(async_db, 'Gestor')
    await _assoc(async_db, gestor.id, c.centro_custo, 'Gestor')
    e = await _criar_eletronico(async_db, c.centro_custo)
    gtoken = await _login(async_client, gestor.email, gsenha)
    create_resp = await async_client.post(
        URL_CESSAO,
        json={
            'eletronico_ids': [e.id],
            'responsavel': 'X',
            'centro_custo_destino': c.centro_custo,
        },
        headers={'Authorization': f'Bearer {gtoken}'},
    )

    resp = await async_client.delete(
        f'{URL_CESSAO}{create_resp.json()["id"]}',
        headers={'Authorization': f'Bearer {gtoken}'},
    )

    assert resp.status_code == HTTPStatus.OK


@pytest.mark.asyncio
@pytest.mark.routers
async def test_delete_cessao_gestor_cc_alheio_proibido(
    async_client, async_db, login_teste
):
    """Gestor que não tem ocupação no CC origem da cessão recebe 403."""
    c1 = await _criar_contrato(async_db)
    c2 = await _criar_contrato(async_db)
    e = await _criar_eletronico(async_db, c1.centro_custo)
    # admin cria a cessão
    create_resp = await async_client.post(
        URL_CESSAO,
        json={
            'eletronico_ids': [e.id],
            'responsavel': 'X',
            'centro_custo_destino': c1.centro_custo,
        },
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    cessao_id = create_resp.json()['id']
    gestor_outro, gsenha = await _criar_usuario(async_db, 'Gestor')
    await _assoc(async_db, gestor_outro.id, c2.centro_custo, 'Gestor')
    gtoken = await _login(async_client, gestor_outro.email, gsenha)

    resp = await async_client.delete(
        f'{URL_CESSAO}{cessao_id}',
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
    create_resp = await async_client.post(
        URL_CESSAO,
        json={
            'eletronico_ids': [e.id],
            'responsavel': 'X',
            'centro_custo_destino': c.centro_custo,
        },
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    func, fsenha = await _criar_usuario(async_db)
    await _assoc(async_db, func.id, c.centro_custo, 'Funcionario')
    ftoken = await _login(async_client, func.email, fsenha)

    resp = await async_client.delete(
        f'{URL_CESSAO}{create_resp.json()["id"]}',
        headers={'Authorization': f'Bearer {ftoken}'},
    )

    assert resp.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
@pytest.mark.routers
async def test_delete_cessao_nao_encontrada(async_client, login_teste):
    resp = await async_client.delete(
        f'{URL_CESSAO}99999',
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    assert resp.status_code == HTTPStatus.NOT_FOUND


# ─── NOTIFICAÇÕES ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_recebimentos_pendentes_admin_ve_tudo(
    async_client, async_db, login_teste
):
    """Admin vê todas as devoluções pendentes, sem restrição de CC."""
    c = await _criar_contrato(async_db)
    e = await _criar_eletronico(async_db, c.centro_custo)
    create_resp = await async_client.post(
        URL_CESSAO,
        json={
            'eletronico_ids': [e.id],
            'responsavel': 'X',
            'centro_custo_destino': c.centro_custo,
        },
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    cessao_id = create_resp.json()['id']
    # alguém devolve (admin mesmo)
    await async_client.put(
        f'{URL_CESSAO}{cessao_id}/devolver',
        json={'eletronico_ids': [e.id]},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    resp = await async_client.get(
        f'{URL_CESSAO}recebimentos/pendentes-gestor',
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.OK
    assert resp.json()['count'] >= 1


@pytest.mark.asyncio
@pytest.mark.routers
async def test_recebimentos_pendentes_gestor_filtra_por_cc(
    async_client, async_db, login_teste
):
    """Gestor só vê pendentes dos CCs onde é Gestor."""
    c1 = await _criar_contrato(async_db)
    c2 = await _criar_contrato(async_db)
    # gestor só em c1
    gestor, gsenha = await _criar_usuario(async_db, 'Gestor')
    await _assoc(async_db, gestor.id, c1.centro_custo, 'Gestor')

    e_c1 = await _criar_eletronico(async_db, c1.centro_custo)
    e_c2 = await _criar_eletronico(async_db, c2.centro_custo)
    # admin cria + devolve as duas
    for cc, e in [(c1, e_c1), (c2, e_c2)]:
        create_resp = await async_client.post(
            URL_CESSAO,
            json={
                'eletronico_ids': [e.id],
                'responsavel': 'X',
                'centro_custo_destino': cc.centro_custo,
            },
            headers={'Authorization': f'Bearer {login_teste["token"]}'},
        )
        await async_client.put(
            f'{URL_CESSAO}{create_resp.json()["id"]}/devolver',
            json={'eletronico_ids': [e.id]},
            headers={'Authorization': f'Bearer {login_teste["token"]}'},
        )

    gtoken = await _login(async_client, gestor.email, gsenha)
    resp = await async_client.get(
        f'{URL_CESSAO}recebimentos/pendentes-gestor',
        headers={'Authorization': f'Bearer {gtoken}'},
    )

    assert resp.status_code == HTTPStatus.OK
    # vê só do c1 (1 lote)
    assert resp.json()['count'] == 1


@pytest.mark.asyncio
@pytest.mark.routers
async def test_recebimentos_pendentes_funcionario_vazio(
    async_client, async_db, login_teste
):
    """Funcionário (sem ocupação Gestor em nenhum CC) recebe count 0."""
    c = await _criar_contrato(async_db)
    e = await _criar_eletronico(async_db, c.centro_custo)
    func, fsenha = await _criar_usuario(async_db)
    await _assoc(async_db, func.id, c.centro_custo, 'Funcionario')
    create_resp = await async_client.post(
        URL_CESSAO,
        json={
            'eletronico_ids': [e.id],
            'responsavel': 'X',
            'centro_custo_destino': c.centro_custo,
        },
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    await async_client.put(
        f'{URL_CESSAO}{create_resp.json()["id"]}/devolver',
        json={'eletronico_ids': [e.id]},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    ftoken = await _login(async_client, func.email, fsenha)
    resp = await async_client.get(
        f'{URL_CESSAO}recebimentos/pendentes-gestor',
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
    create_resp = await async_client.post(
        URL_CESSAO,
        json={
            'eletronico_ids': [e.id],
            'responsavel': 'X',
            'centro_custo_destino': c.centro_custo,
        },
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    await async_client.put(
        f'{URL_CESSAO}{create_resp.json()["id"]}/devolver',
        json={'eletronico_ids': [e.id]},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    # antes de marcar: count >= 1
    before = await async_client.get(
        f'{URL_CESSAO}recebimentos/pendentes-gestor',
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    assert before.json()['count'] >= 1

    mark = await async_client.put(
        f'{URL_CESSAO}recebimentos/visto',
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    assert mark.status_code == HTTPStatus.OK
    assert mark.json()['marcadas'] >= 1

    # depois: 0
    after = await async_client.get(
        f'{URL_CESSAO}recebimentos/pendentes-gestor',
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    assert after.json()['count'] == 0
