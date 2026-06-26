from http import HTTPStatus
from itertools import count

import pytest

from backend.model.contratos import Contrato
from backend.model.user import User
from backend.security.security import Security

URL = '/contratos/'

_counter = count(1)


def _n():
    return next(_counter)


async def _criar_usuario(async_db, tipo='Gestor'):
    n = _n()
    security = Security()
    senha = 'senha123'
    u = User(
        nome=f'ContUser{n}',
        email=f'cont{n}@test.com',
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


async def _criar_contrato_db(async_db, cc=None):
    cc = cc or f'C{_n():03d}'
    c = Contrato(centro_custo=cc, descricao=f'Contrato {cc}')
    async_db.add(c)
    await async_db.flush()
    return c


def _assert_campos(json_resp: dict, expected: dict) -> None:
    for key, value in expected.items():
        assert json_resp.get(key) == value, (
            f'{key}: esperado {value!r}, recebido {json_resp.get(key)!r}'
        )


# ─── CRUD básico ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_contrato(async_client, contrato_teste, login_teste):
    resp = await async_client.post(
        URL,
        json=contrato_teste,
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.CREATED
    _assert_campos(resp.json(), contrato_teste)


@pytest.mark.asyncio
@pytest.mark.routers
async def test_get_contratos(async_client, contrato_teste, login_teste):
    await async_client.post(
        URL,
        json=contrato_teste,
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    resp = await async_client.get(
        URL,
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.OK
    assert isinstance(resp.json()['contratos'], list)
    _assert_campos(resp.json()['contratos'][0], contrato_teste)


@pytest.mark.asyncio
@pytest.mark.routers
async def test_update_contrato(async_client, contrato_teste, login_teste):
    await async_client.post(
        URL,
        json=contrato_teste,
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    updated = {
        'centro_custo': contrato_teste['centro_custo'],
        'descricao': 'Descricao atualizada',
    }
    resp = await async_client.put(
        f'{URL}{contrato_teste["centro_custo"]}',
        json=updated,
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.OK
    _assert_campos(resp.json(), updated)


@pytest.mark.asyncio
@pytest.mark.routers
async def test_update_contrato_nao_encontrado(
    async_client, login_teste
):
    resp = await async_client.put(
        f'{URL}XXXX',
        json={'centro_custo': 'XXXX', 'descricao': 'X'},
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
@pytest.mark.routers
async def test_delete_contrato(async_client, contrato_teste, login_teste):
    await async_client.post(
        URL,
        json=contrato_teste,
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    resp = await async_client.delete(
        f'{URL}{contrato_teste["centro_custo"]}',
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.OK
    _assert_campos(resp.json(), contrato_teste)


@pytest.mark.asyncio
@pytest.mark.routers
async def test_delete_contrato_nao_encontrado(
    async_client, login_teste
):
    resp = await async_client.delete(
        f'{URL}XXXX',
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.NOT_FOUND


# ─── SRP: create() acumula criação do contrato + associação Gestor ───────────
# ContratoService.create() persiste dois objetos distintos num único método.
# Pelo SRP, a criação da associação deveria ser delegada ao serviço de
# associações. Os testes abaixo documentam esse acoplamento.


@pytest.mark.asyncio
@pytest.mark.routers
async def test_criar_contrato_gera_associacao_gestor_automaticamente(
    async_client, contrato_teste, login_teste
):
    """
    ContratoService.create() cria o contrato e, como side-effect,
    também cria a associação do criador como Gestor — responsabilidade
    dupla num único método (SRP).
    """
    resp = await async_client.post(
        URL,
        json=contrato_teste,
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    assert resp.status_code == HTTPStatus.CREATED
    cc = contrato_teste['centro_custo']

    assoc_resp = await async_client.get(
        '/associacoes/contratos/',
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )
    gestores = [
        a for a in assoc_resp.json()['associacoes']
        if a['centro_custo'] == cc and a['ocupacao'] == 'Gestor'
    ]
    assert len(gestores) == 1


@pytest.mark.asyncio
@pytest.mark.routers
async def test_associacao_gerada_aponta_para_o_criador(
    async_client, async_db
):
    """
    A associação gerada como side-effect de create() deve pertencer
    ao usuário que executou a criação, não a qualquer Admin genérico.
    """
    gestor, gsenha = await _criar_usuario(async_db, tipo='Gestor')
    gtoken = await _login(async_client, gestor.email, gsenha)
    cc = f'CT{_n()}'

    resp = await async_client.post(
        URL,
        json={'centro_custo': cc, 'descricao': 'Criador correto'},
        headers={'Authorization': f'Bearer {gtoken}'},
    )
    assert resp.status_code == HTTPStatus.CREATED

    assoc_resp = await async_client.get(
        '/associacoes/contratos/',
        headers={'Authorization': f'Bearer {gtoken}'},
    )
    assoc_cc = [
        a for a in assoc_resp.json()['associacoes']
        if a['centro_custo'] == cc
    ]
    assert len(assoc_cc) == 1
    assert assoc_cc[0]['user_id'] == gestor.id
    assert assoc_cc[0]['ocupacao'] == 'Gestor'


@pytest.mark.asyncio
@pytest.mark.routers
async def test_criar_contrato_duplicado_retorna_conflict(
    async_client, async_db
):
    gestor, gsenha = await _criar_usuario(async_db, tipo='Gestor')
    gtoken = await _login(async_client, gestor.email, gsenha)
    cc = f'DUP{_n()}'
    payload = {'centro_custo': cc, 'descricao': 'X'}

    headers = {'Authorization': f'Bearer {gtoken}'}
    await async_client.post(URL, json=payload, headers=headers)
    resp = await async_client.post(URL, json=payload, headers=headers)

    assert resp.status_code == HTTPStatus.CONFLICT


# ─── Autorização de escrita ──────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_funcionario_nao_pode_criar_contrato(async_client, async_db):
    n = _n()
    security = Security()
    func = User(
        nome=f'Func{n}',
        email=f'func{n}@test.com',
        senha=security.get_senha_hash('senha123'),
        tipo='Funcionario',
    )
    async_db.add(func)
    await async_db.flush()
    await async_db.refresh(func)
    token = await _login(async_client, func.email, 'senha123')

    resp = await async_client.post(
        URL,
        json={'centro_custo': f'FC{_n()}', 'descricao': 'X'},
        headers={'Authorization': f'Bearer {token}'},
    )

    assert resp.status_code == HTTPStatus.FORBIDDEN


# ─── Rename do código do CC (propagação) ─────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_update_contrato_rename_propaga_eletronico(
    async_client, login_teste
):
    """Renomear o código do CC propaga para os equipamentos."""
    h = {'Authorization': f'Bearer {login_teste["token"]}'}
    await async_client.post(
        URL, json={'centro_custo': 'RN01', 'descricao': 'Origem'}, headers=h
    )
    el = await async_client.post(
        '/eletronicos/',
        json={
            'numero_serie': 'SN-RN01',
            'numero_patrimonio': 'PAT-RN01',
            'nome': 'Equip RN',
            'tipo': 'Scanner',
            'status': 'Interno',
            'centro_custo': 'RN01',
        },
        headers=h,
    )
    assert el.status_code == HTTPStatus.CREATED
    el_id = el.json()['id']

    resp = await async_client.put(
        f'{URL}RN01',
        json={'centro_custo': 'RN02', 'descricao': 'Origem'},
        headers=h,
    )
    assert resp.status_code == HTTPStatus.OK
    assert resp.json()['centro_custo'] == 'RN02'

    el_get = await async_client.get('/eletronicos/', headers=h)
    target = next(
        (e for e in el_get.json()['eletronicos'] if e['id'] == el_id),
        None,
    )
    assert target is not None
    assert target['centro_custo'] == 'RN02'

    ccs = await async_client.get(URL, headers=h)
    codigos = {c['centro_custo'] for c in ccs.json()['contratos']}
    assert 'RN01' not in codigos
    assert 'RN02' in codigos


@pytest.mark.asyncio
@pytest.mark.routers
async def test_update_contrato_rename_propaga_associacao(
    async_client, login_teste
):
    """Renomear o código do CC propaga para as associações user-CC."""
    h = {'Authorization': f'Bearer {login_teste["token"]}'}
    await async_client.post(
        URL, json={'centro_custo': 'RN05', 'descricao': 'X'}, headers=h
    )

    resp = await async_client.put(
        f'{URL}RN05',
        json={'centro_custo': 'RN06', 'descricao': 'X'},
        headers=h,
    )
    assert resp.status_code == HTTPStatus.OK

    assoc = await async_client.get('/associacoes/contratos/', headers=h)
    rows = assoc.json()['associacoes']
    assert any(a['centro_custo'] == 'RN06' for a in rows)
    assert all(a['centro_custo'] != 'RN05' for a in rows)


@pytest.mark.asyncio
@pytest.mark.routers
async def test_update_contrato_rename_colisao_conflict(
    async_client, login_teste
):
    """Renomear para um código já existente retorna 409."""
    h = {'Authorization': f'Bearer {login_teste["token"]}'}
    await async_client.post(
        URL, json={'centro_custo': 'RN03', 'descricao': 'A'}, headers=h
    )
    await async_client.post(
        URL, json={'centro_custo': 'RN04', 'descricao': 'B'}, headers=h
    )

    resp = await async_client.put(
        f'{URL}RN03',
        json={'centro_custo': 'RN04', 'descricao': 'A'},
        headers=h,
    )
    assert resp.status_code == HTTPStatus.CONFLICT
