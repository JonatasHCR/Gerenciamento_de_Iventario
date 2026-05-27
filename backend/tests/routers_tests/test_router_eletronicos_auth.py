"""
Tests adicionais para cobrir branches de autorização per-CC em
EletronicoService (create/update/delete), o endpoint admin de criação
de usuário, e testes ISP/DIP documentando o design do UserContext.
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
URL_USER_ADMIN = '/users/admin'
URL_USER = '/users/'

_counter = count(1)


def _n():
    return next(_counter)


async def _criar_usuario(async_db, nome, tipo='Funcionario'):
    security = Security()
    senha = 'senha123'
    u = User(
        nome=nome,
        email=f'{nome}@eauth.com',
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
    c = Contrato(centro_custo=cc, descricao=f'CC {cc}')
    async_db.add(c)
    await async_db.flush()
    return c


async def _associar_cc(async_db, user_id, cc, ocupacao):
    a = AssociacaoUserContrato(
        user_id=user_id, centro_custo=cc, ocupacao=ocupacao
    )
    async_db.add(a)
    await async_db.flush()


async def _criar_eletronico_db(async_db, cc, **overrides):
    n = _n()
    defaults = dict(
        numero_serie=f'SN-EA{n}',
        numero_patrimonio=f'PAT-EA{n}',
        nome=f'EquipEA{n}',
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


# ─── _assert_ownership branches ───────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_update_eletronico_funcionario_proprio(
    async_client, async_db
):
    """Funcionario só edita o próprio eletrônico (com associação)."""
    await _criar_contrato(async_db, 'EAF')
    func, fsenha = await _criar_usuario(async_db, 'fea1')
    await _associar_cc(async_db, func.id, 'EAF', 'Funcionario')
    e = await _criar_eletronico_db(async_db, 'EAF')
    await _associar_user_eletronico(async_db, func.id, e.id)
    token = await _login(async_client, func.email, fsenha)

    resp = await async_client.put(
        f'{URL}{e.id}',
        json={
            'numero_serie': e.numero_serie,
            'numero_patrimonio': e.numero_patrimonio,
            'nome': 'Novo Nome',
            'tipo': 'Notbook',
            'status': 'Interno',
            'centro_custo': 'EAF',
        },
        headers={'Authorization': f'Bearer {token}'},
    )

    assert resp.status_code == HTTPStatus.OK
    assert resp.json()['nome'] == 'Novo Nome'


@pytest.mark.asyncio
@pytest.mark.routers
async def test_update_eletronico_funcionario_alheio_proibido(
    async_client, async_db
):
    """Funcionário SEM associação ao eletrônico (mesmo CC) → 403."""
    await _criar_contrato(async_db, 'EAB')
    func, fsenha = await _criar_usuario(async_db, 'fea2')
    await _associar_cc(async_db, func.id, 'EAB', 'Funcionario')
    e = await _criar_eletronico_db(async_db, 'EAB')  # sem associação
    token = await _login(async_client, func.email, fsenha)

    resp = await async_client.put(
        f'{URL}{e.id}',
        json={
            'numero_serie': e.numero_serie,
            'numero_patrimonio': e.numero_patrimonio,
            'nome': 'X',
            'tipo': 'Notbook',
            'status': 'Interno',
            'centro_custo': 'EAB',
        },
        headers={'Authorization': f'Bearer {token}'},
    )

    assert resp.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
@pytest.mark.routers
async def test_delete_eletronico_usuario_fora_cc_proibido(
    async_client, async_db
):
    """Usuário sem ocupação no CC do eletrônico → 403."""
    await _criar_contrato(async_db, 'EAC1')
    await _criar_contrato(async_db, 'EAC2')
    e = await _criar_eletronico_db(async_db, 'EAC1')
    outsider, osenha = await _criar_usuario(async_db, 'fea3')
    await _associar_cc(async_db, outsider.id, 'EAC2', 'Gestor')
    token = await _login(async_client, outsider.email, osenha)

    resp = await async_client.delete(
        f'{URL}{e.id}',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert resp.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
@pytest.mark.routers
async def test_update_eletronico_gestor_outro_cc_proibido(
    async_client, async_db
):
    """Gestor de outro CC tenta editar eletrônico do CC alheio → 403."""
    await _criar_contrato(async_db, 'EGO1')
    await _criar_contrato(async_db, 'EGO2')
    gestor, gsenha = await _criar_usuario(async_db, 'fea4', 'Gestor')
    await _associar_cc(async_db, gestor.id, 'EGO2', 'Gestor')
    e = await _criar_eletronico_db(async_db, 'EGO1')
    token = await _login(async_client, gestor.email, gsenha)

    resp = await async_client.delete(
        f'{URL}{e.id}',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert resp.status_code == HTTPStatus.FORBIDDEN


# ─── create() branches ─────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_eletronico_funcionario_auto_associa(
    async_client, async_db
):
    """Funcionário cria eletrônico e o backend auto-associa."""
    await _criar_contrato(async_db, 'FCA')
    func, fsenha = await _criar_usuario(async_db, 'fea5')
    await _associar_cc(async_db, func.id, 'FCA', 'Funcionario')
    token = await _login(async_client, func.email, fsenha)

    create_resp = await async_client.post(
        URL,
        json={
            'numero_serie': 'FCA-SN-1',
            'numero_patrimonio': 'FCA-PAT-1',
            'nome': 'Equip FCA',
            'tipo': 'Notbook',
            'status': 'Interno',
            'centro_custo': 'FCA',
        },
        headers={'Authorization': f'Bearer {token}'},
    )

    assert create_resp.status_code == HTTPStatus.CREATED
    eletronico_id = create_resp.json()['id']

    # Verifica auto-associação: lista de assoc deve conter o eletrônico
    list_resp = await async_client.get(
        '/associacoes/eletronicos/',
        headers={'Authorization': f'Bearer {token}'},
    )
    assocs = list_resp.json()['associacoes']
    assert any(
        a['user_id'] == func.id and a['eletronico_id'] == eletronico_id
        for a in assocs
    )


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_eletronico_sem_ocupacao_proibido(
    async_client, async_db
):
    """Usuário sem nenhuma ocupação no CC alvo → 403."""
    await _criar_contrato(async_db, 'SCO')
    func, fsenha = await _criar_usuario(async_db, 'fea6')
    # SEM associação ao CC SCO
    token = await _login(async_client, func.email, fsenha)

    resp = await async_client.post(
        URL,
        json={
            'numero_serie': 'SCO-SN-1',
            'numero_patrimonio': 'SCO-PAT-1',
            'nome': 'X',
            'tipo': 'Notbook',
            'status': 'Interno',
            'centro_custo': 'SCO',
        },
        headers={'Authorization': f'Bearer {token}'},
    )

    assert resp.status_code == HTTPStatus.FORBIDDEN


# ─── POST /users/admin ────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_user_admin_endpoint(
    async_client, login_teste
):
    """POST /users/admin criar como admin tipo específico."""
    resp = await async_client.post(
        URL_USER_ADMIN,
        json={
            'nome': 'NovoGestor',
            'email': 'novogestor@adm.com',
            'senha': 'senha123',
            'tipo': 'Gestor',
        },
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.CREATED
    assert resp.json()['tipo'] == 'Gestor'


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_user_admin_endpoint_nao_admin_proibido(
    async_client, async_db
):
    """Não-Admin chamando /users/admin → 403."""
    func, fsenha = await _criar_usuario(async_db, 'feauser')
    token = await _login(async_client, func.email, fsenha)

    resp = await async_client.post(
        URL_USER_ADMIN,
        json={
            'nome': 'X',
            'email': 'x@adm.com',
            'senha': 'senha123',
            'tipo': 'Gestor',
        },
        headers={'Authorization': f'Bearer {token}'},
    )

    assert resp.status_code == HTTPStatus.FORBIDDEN


# ─── POST /users/ (auto-registro força Funcionario) ───────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_autoregistro_forca_funcionario(async_client):
    """POST /users/ público — qualquer tipo enviado vira Funcionario."""
    resp = await async_client.post(
        URL_USER,
        json={
            'nome': 'AutoReg',
            'email': 'autoreg@p.com',
            'senha': 'senha123',
            'tipo': 'Admin',  # tentativa de escalar
        },
    )

    assert resp.status_code == HTTPStatus.CREATED
    assert resp.json()['tipo'] == 'Funcionario'
    # senha não vaza
    assert 'senha' not in resp.json()


# ─── GET /users/ visibilidade Funcionario só do CC ────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_funcionario_ve_apenas_users_do_proprio_cc(
    async_client, async_db
):
    await _criar_contrato(async_db, 'VUC')
    await _criar_contrato(async_db, 'VUD')
    func, fsenha = await _criar_usuario(async_db, 'fvuc')
    await _associar_cc(async_db, func.id, 'VUC', 'Funcionario')
    colega, _ = await _criar_usuario(async_db, 'colegavuc')
    await _associar_cc(async_db, colega.id, 'VUC', 'Funcionario')
    forasteiro, _ = await _criar_usuario(async_db, 'forasteiro')
    await _associar_cc(async_db, forasteiro.id, 'VUD', 'Funcionario')
    token = await _login(async_client, func.email, fsenha)

    resp = await async_client.get(
        '/users/',
        headers={'Authorization': f'Bearer {token}'},
    )

    emails = {u['email'] for u in resp.json()['users']}
    assert colega.email in emails
    assert forasteiro.email not in emails


# ─── ISP: UserContext carregado completo — papéis privilegiados
# funcionam mesmo sem centros_custo/ocupacoes populados ──────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_admin_sem_associacoes_cc_lista_todos_eletronicos(
    async_client, async_db
):
    """
    ISP: UserContext sempre hidrata centros_custo/ocupacoes/is_privileged/
    is_tecnico_ti, mas EletronicoService só consulta is_privileged para
    Admins. Admin sem nenhuma associação de CC enxerga todos os eletrônicos.
    """
    await _criar_contrato(async_db, 'ISPA')
    e = await _criar_eletronico_db(async_db, 'ISPA')
    admin, asenha = await _criar_usuario(
        async_db, f'admisp{_n()}', 'Admin'
    )
    token = await _login(async_client, admin.email, asenha)

    resp = await async_client.get(
        URL, headers={'Authorization': f'Bearer {token}'}
    )

    ids = {i['id'] for i in resp.json()['eletronicos']}
    assert e.id in ids


@pytest.mark.asyncio
@pytest.mark.routers
async def test_tecnico_ti_sem_associacoes_cc_lista_todos_eletronicos(
    async_client, async_db
):
    """
    ISP: EletronicoService consulta is_tecnico_ti e ignora
    centros_custo/ocupacoes nesse caminho. Tecnico_TI sem associação de
    CC vê todos os eletrônicos.
    """
    await _criar_contrato(async_db, 'ISPT')
    e = await _criar_eletronico_db(async_db, 'ISPT')
    ti, tsenha = await _criar_usuario(
        async_db, f'tiisp{_n()}', 'Tecnico_TI'
    )
    token = await _login(async_client, ti.email, tsenha)

    resp = await async_client.get(
        URL, headers={'Authorization': f'Bearer {token}'}
    )

    ids = {i['id'] for i in resp.json()['eletronicos']}
    assert e.id in ids


# ─── DIP: sessão injetada via override — mudanças do service refletem
# no async_db do teste sem commit adicional ────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_dip_sessao_injetada_reflete_mudancas_do_service(
    async_client, async_db
):
    """
    DIP: a sessão é injetada via dependency_overrides, não criada
    internamente pelo service. Por isso mudanças feitas pelo service
    (status → Externo ao criar uma cessão) refletem imediatamente no
    async_db do teste via refresh — sem commit explícito no teste.
    """
    await _criar_contrato(async_db, 'DIP1')
    e = await _criar_eletronico_db(async_db, 'DIP1', status='Interno')
    admin, asenha = await _criar_usuario(
        async_db, f'dipadm{_n()}', 'Admin'
    )
    token = await _login(async_client, admin.email, asenha)

    await async_client.post(
        '/cessoes/',
        json={
            'eletronico_ids': [e.id],
            'responsavel': 'DIP',
            'centro_custo_destino': 'DIP1',
        },
        headers={'Authorization': f'Bearer {token}'},
    )

    await async_db.refresh(e)
    assert e.status == 'Externo'
