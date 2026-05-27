from http import HTTPStatus
from itertools import count

import pytest
from sqlalchemy import select

from backend.model.associacao_user_contrato import AssociacaoUserContrato
from backend.model.contratos import Contrato
from backend.model.user import User
from backend.security.security import Security

URL = '/solicitacoes'

_counter = count(1)


def _n():
    return next(_counter)


async def _criar_usuario(async_db, tipo='Funcionario'):
    n = _n()
    security = Security()
    senha = 'senha123'
    u = User(
        nome=f'SolUser{n}',
        email=f'sol{n}@test.com',
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
    cc = cc or f'SC{_n():03d}'
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


async def _solicitar_entrada(async_client, token, cc, ocupacao='Funcionario'):
    return await async_client.post(
        f'{URL}/entrada-cc',
        json={'centro_custo': cc, 'ocupacao_solicitada': ocupacao},
        headers={'Authorization': f'Bearer {token}'},
    )


# ─── entrada-cc: criação ─────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_entrada_cc(async_client, async_db):
    c = await _criar_contrato(async_db)
    func, fsenha = await _criar_usuario(async_db)
    token = await _login(async_client, func.email, fsenha)

    resp = await _solicitar_entrada(async_client, token, c.centro_custo)

    assert resp.status_code == HTTPStatus.CREATED
    data = resp.json()
    assert data['tipo'] == 'entrada_cc'
    assert data['status'] == 'pendente'
    assert data['convidado_por_id'] is None


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_entrada_cc_nao_encontrado(async_client, async_db):
    func, fsenha = await _criar_usuario(async_db)
    token = await _login(async_client, func.email, fsenha)

    resp = await _solicitar_entrada(async_client, token, 'XXXX')

    assert resp.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_entrada_cc_duplicada(async_client, async_db):
    c = await _criar_contrato(async_db)
    func, fsenha = await _criar_usuario(async_db)
    token = await _login(async_client, func.email, fsenha)

    await _solicitar_entrada(async_client, token, c.centro_custo)
    resp = await _solicitar_entrada(async_client, token, c.centro_custo)

    assert resp.status_code == HTTPStatus.CONFLICT


# ─── convite-cc ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_convite_cc_gestor(async_client, async_db):
    c = await _criar_contrato(async_db)
    gestor, gsenha = await _criar_usuario(async_db, 'Gestor')
    await _associar(async_db, gestor.id, c.centro_custo, 'Gestor')
    convidado, _ = await _criar_usuario(async_db)
    gtoken = await _login(async_client, gestor.email, gsenha)

    resp = await async_client.post(
        f'{URL}/convite-cc',
        json={
            'solicitante_id': convidado.id,
            'centro_custo': c.centro_custo,
            'ocupacao_solicitada': 'Funcionario',
        },
        headers={'Authorization': f'Bearer {gtoken}'},
    )

    assert resp.status_code == HTTPStatus.CREATED
    assert resp.json()['convidado_por_id'] == gestor.id


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_convite_cc_nao_autorizado(async_client, async_db):
    c = await _criar_contrato(async_db)
    func, fsenha = await _criar_usuario(async_db)
    convidado, _ = await _criar_usuario(async_db)
    ftoken = await _login(async_client, func.email, fsenha)

    resp = await async_client.post(
        f'{URL}/convite-cc',
        json={
            'solicitante_id': convidado.id,
            'centro_custo': c.centro_custo,
            'ocupacao_solicitada': 'Funcionario',
        },
        headers={'Authorization': f'Bearer {ftoken}'},
    )

    assert resp.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_convite_cc_subgestor_pode_convidar_funcionario(
    async_client, async_db
):
    c = await _criar_contrato(async_db)
    subg, ssenha = await _criar_usuario(async_db, 'Subgestor')
    await _associar(async_db, subg.id, c.centro_custo, 'Subgestor')
    convidado, _ = await _criar_usuario(async_db)
    stoken = await _login(async_client, subg.email, ssenha)

    resp = await async_client.post(
        f'{URL}/convite-cc',
        json={
            'solicitante_id': convidado.id,
            'centro_custo': c.centro_custo,
            'ocupacao_solicitada': 'Funcionario',
        },
        headers={'Authorization': f'Bearer {stoken}'},
    )

    assert resp.status_code == HTTPStatus.CREATED


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_convite_cc_subgestor_nao_pode_convidar_gestor(
    async_client, async_db
):
    """OCP: regra Subgestor é hardcoded — só pode convidar Funcionario."""
    c = await _criar_contrato(async_db)
    subg, ssenha = await _criar_usuario(async_db, 'Subgestor')
    await _associar(async_db, subg.id, c.centro_custo, 'Subgestor')
    convidado, _ = await _criar_usuario(async_db)
    stoken = await _login(async_client, subg.email, ssenha)

    resp = await async_client.post(
        f'{URL}/convite-cc',
        json={
            'solicitante_id': convidado.id,
            'centro_custo': c.centro_custo,
            'ocupacao_solicitada': 'Gestor',
        },
        headers={'Authorization': f'Bearer {stoken}'},
    )

    assert resp.status_code == HTTPStatus.FORBIDDEN


# ─── cargo-inicial ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_create_cargo_inicial(async_client, async_db):
    func, fsenha = await _criar_usuario(async_db)
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
async def test_create_cargo_inicial_duplicado(async_client, async_db):
    func, fsenha = await _criar_usuario(async_db)
    token = await _login(async_client, func.email, fsenha)

    await async_client.post(
        f'{URL}/cargo-inicial',
        json={'cargo_solicitado': 'Gestor'},
        headers={'Authorization': f'Bearer {token}'},
    )
    resp = await async_client.post(
        f'{URL}/cargo-inicial',
        json={'cargo_solicitado': 'Gestor'},
        headers={'Authorization': f'Bearer {token}'},
    )

    assert resp.status_code == HTTPStatus.CONFLICT


# ─── aprovar ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_aprovar_entrada_cc_gestor(async_client, async_db):
    c = await _criar_contrato(async_db)
    gestor, gsenha = await _criar_usuario(async_db, 'Gestor')
    await _associar(async_db, gestor.id, c.centro_custo, 'Gestor')
    func, fsenha = await _criar_usuario(async_db)
    gtoken = await _login(async_client, gestor.email, gsenha)
    ftoken = await _login(async_client, func.email, fsenha)

    sol_resp = await _solicitar_entrada(async_client, ftoken, c.centro_custo)
    sol_id = sol_resp.json()['id']

    resp = await async_client.put(
        f'{URL}/{sol_id}/aprovar',
        headers={'Authorization': f'Bearer {gtoken}'},
    )

    assert resp.status_code == HTTPStatus.OK
    assert resp.json()['status'] == 'aprovada'


@pytest.mark.asyncio
@pytest.mark.routers
async def test_aprovar_entrada_cc_nao_autorizado(async_client, async_db):
    c = await _criar_contrato(async_db)
    func1, f1senha = await _criar_usuario(async_db)
    func2, f2senha = await _criar_usuario(async_db)
    f1token = await _login(async_client, func1.email, f1senha)
    f2token = await _login(async_client, func2.email, f2senha)

    sol_resp = await _solicitar_entrada(async_client, f1token, c.centro_custo)
    sol_id = sol_resp.json()['id']

    resp = await async_client.put(
        f'{URL}/{sol_id}/aprovar',
        headers={'Authorization': f'Bearer {f2token}'},
    )

    assert resp.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
@pytest.mark.routers
async def test_aprovar_entrada_cc_subgestor_pode_aprovar_funcionario(
    async_client, async_db
):
    c = await _criar_contrato(async_db)
    subg, ssenha = await _criar_usuario(async_db, 'Subgestor')
    await _associar(async_db, subg.id, c.centro_custo, 'Subgestor')
    func, fsenha = await _criar_usuario(async_db)
    stoken = await _login(async_client, subg.email, ssenha)
    ftoken = await _login(async_client, func.email, fsenha)

    sol_resp = await _solicitar_entrada(async_client, ftoken, c.centro_custo)
    sol_id = sol_resp.json()['id']

    resp = await async_client.put(
        f'{URL}/{sol_id}/aprovar',
        headers={'Authorization': f'Bearer {stoken}'},
    )

    assert resp.status_code == HTTPStatus.OK


@pytest.mark.asyncio
@pytest.mark.routers
async def test_aprovar_entrada_cc_subgestor_nao_pode_aprovar_gestor(
    async_client, async_db
):
    """OCP: Subgestor hardcoded — não aprova ocupações acima de Funcionario."""
    c = await _criar_contrato(async_db)
    subg, ssenha = await _criar_usuario(async_db, 'Subgestor')
    await _associar(async_db, subg.id, c.centro_custo, 'Subgestor')
    func, fsenha = await _criar_usuario(async_db)
    stoken = await _login(async_client, subg.email, ssenha)
    ftoken = await _login(async_client, func.email, fsenha)

    sol_resp = await _solicitar_entrada(
        async_client, ftoken, c.centro_custo, ocupacao='Gestor'
    )
    sol_id = sol_resp.json()['id']

    resp = await async_client.put(
        f'{URL}/{sol_id}/aprovar',
        headers={'Authorization': f'Bearer {stoken}'},
    )

    assert resp.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
@pytest.mark.routers
async def test_aprovar_convite_pelo_convidado(async_client, async_db):
    c = await _criar_contrato(async_db)
    gestor, gsenha = await _criar_usuario(async_db, 'Gestor')
    await _associar(async_db, gestor.id, c.centro_custo, 'Gestor')
    convidado, csenha = await _criar_usuario(async_db)
    gtoken = await _login(async_client, gestor.email, gsenha)
    ctoken = await _login(async_client, convidado.email, csenha)

    sol_resp = await async_client.post(
        f'{URL}/convite-cc',
        json={
            'solicitante_id': convidado.id,
            'centro_custo': c.centro_custo,
            'ocupacao_solicitada': 'Funcionario',
        },
        headers={'Authorization': f'Bearer {gtoken}'},
    )
    sol_id = sol_resp.json()['id']

    resp = await async_client.put(
        f'{URL}/{sol_id}/aprovar',
        headers={'Authorization': f'Bearer {ctoken}'},
    )

    assert resp.status_code == HTTPStatus.OK
    assert resp.json()['status'] == 'aprovada'


@pytest.mark.asyncio
@pytest.mark.routers
async def test_aprovar_convite_por_terceiro_proibido(async_client, async_db):
    c = await _criar_contrato(async_db)
    gestor, gsenha = await _criar_usuario(async_db, 'Gestor')
    await _associar(async_db, gestor.id, c.centro_custo, 'Gestor')
    convidado, _ = await _criar_usuario(async_db)
    outro, osenha = await _criar_usuario(async_db)
    gtoken = await _login(async_client, gestor.email, gsenha)
    otoken = await _login(async_client, outro.email, osenha)

    sol_resp = await async_client.post(
        f'{URL}/convite-cc',
        json={
            'solicitante_id': convidado.id,
            'centro_custo': c.centro_custo,
            'ocupacao_solicitada': 'Funcionario',
        },
        headers={'Authorization': f'Bearer {gtoken}'},
    )
    sol_id = sol_resp.json()['id']

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
    func, fsenha = await _criar_usuario(async_db)
    ftoken = await _login(async_client, func.email, fsenha)

    sol_resp = await async_client.post(
        f'{URL}/cargo-inicial',
        json={'cargo_solicitado': 'Gestor'},
        headers={'Authorization': f'Bearer {ftoken}'},
    )
    sol_id = sol_resp.json()['id']

    resp = await async_client.put(
        f'{URL}/{sol_id}/aprovar',
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.OK
    assert resp.json()['status'] == 'aprovada'


@pytest.mark.asyncio
@pytest.mark.routers
async def test_aprovar_cargo_inicial_nao_admin_proibido(
    async_client, async_db
):
    """OCP: aprovação de cargo_inicial hardcoded para Admin — só Admin pode."""
    func, fsenha = await _criar_usuario(async_db)
    gestor, gsenha = await _criar_usuario(async_db, 'Gestor')
    ftoken = await _login(async_client, func.email, fsenha)
    gtoken = await _login(async_client, gestor.email, gsenha)

    sol_resp = await async_client.post(
        f'{URL}/cargo-inicial',
        json={'cargo_solicitado': 'Gestor'},
        headers={'Authorization': f'Bearer {ftoken}'},
    )
    sol_id = sol_resp.json()['id']

    resp = await async_client.put(
        f'{URL}/{sol_id}/aprovar',
        headers={'Authorization': f'Bearer {gtoken}'},
    )

    assert resp.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
@pytest.mark.routers
async def test_aprovar_ja_aprovada_retorna_bad_request(
    async_client, async_db, login_teste
):
    func, fsenha = await _criar_usuario(async_db)
    ftoken = await _login(async_client, func.email, fsenha)
    admin_token = login_teste['token']

    sol_resp = await async_client.post(
        f'{URL}/cargo-inicial',
        json={'cargo_solicitado': 'Gestor'},
        headers={'Authorization': f'Bearer {ftoken}'},
    )
    sol_id = sol_resp.json()['id']

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
async def test_aprovar_nao_encontrado(async_client, login_teste):
    resp = await async_client.put(
        f'{URL}/9999/aprovar',
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.NOT_FOUND


# ─── SRP: aprovar() tem branches para tipos distintos num único método ───────
# Um único método cuida de entrada_cc, cargo_inicial e cessao.
# Os testes abaixo verificam que cada branch tem efeitos colaterais isolados.


@pytest.mark.asyncio
@pytest.mark.routers
async def test_aprovar_entrada_cc_nao_altera_tipo_global_do_usuario(
    async_client, async_db, login_teste
):
    """
    SRP: aprovar() contém branches para entrada_cc e cargo_inicial.
    Ao aprovar entrada_cc, apenas a associação deve ser criada.
    O tipo global do usuário NÃO deve mudar.
    """
    c = await _criar_contrato(async_db)
    func, fsenha = await _criar_usuario(async_db)
    ftoken = await _login(async_client, func.email, fsenha)

    sol_resp = await _solicitar_entrada(async_client, ftoken, c.centro_custo)
    sol_id = sol_resp.json()['id']

    await async_client.put(
        f'{URL}/{sol_id}/aprovar',
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    await async_db.refresh(func)
    assert func.tipo == 'Funcionario', (
        'aprovar entrada_cc não deve alterar tipo global'
    )
    result = await async_db.execute(
        select(AssociacaoUserContrato).where(
            AssociacaoUserContrato.user_id == func.id,
            AssociacaoUserContrato.centro_custo == c.centro_custo,
        )
    )
    assert result.scalar_one_or_none() is not None


@pytest.mark.asyncio
@pytest.mark.routers
async def test_aprovar_cargo_inicial_nao_cria_associacao_cc(
    async_client, async_db, login_teste
):
    """
    SRP: aprovar() trata cargo_inicial e entrada_cc no mesmo método.
    Ao aprovar cargo_inicial, apenas o tipo deve mudar —
    nenhuma nova associação CC deve ser criada.
    """
    func, fsenha = await _criar_usuario(async_db)
    ftoken = await _login(async_client, func.email, fsenha)

    result_antes = await async_db.execute(
        select(AssociacaoUserContrato).where(
            AssociacaoUserContrato.user_id == func.id
        )
    )
    total_antes = len(result_antes.scalars().all())

    sol_resp = await async_client.post(
        f'{URL}/cargo-inicial',
        json={'cargo_solicitado': 'Tecnico_TI'},
        headers={'Authorization': f'Bearer {ftoken}'},
    )
    sol_id = sol_resp.json()['id']

    await async_client.put(
        f'{URL}/{sol_id}/aprovar',
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    await async_db.refresh(func)
    assert func.tipo == 'Tecnico_TI'

    result_depois = await async_db.execute(
        select(AssociacaoUserContrato).where(
            AssociacaoUserContrato.user_id == func.id
        )
    )
    total_depois = len(result_depois.scalars().all())
    assert total_depois == total_antes, (
        'aprovar cargo_inicial não deve criar associações CC'
    )


# ─── OCP: autorização por ocupação no CC, não por tipo global ────────────────
# As permissões estão hardcoded com if/elif por tipo/ocupação.
# Os testes documentam que o critério correto é a OCUPAÇÃO no CC específico.


@pytest.mark.asyncio
@pytest.mark.routers
async def test_funcionario_global_com_ocupacao_gestor_pode_aprovar(
    async_client, async_db
):
    """
    OCP: tipo global 'Funcionario' + ocupação 'Gestor' no CC
    deve permitir aprovar — a regra é por ocupação, não por tipo.
    """
    c = await _criar_contrato(async_db)
    func_gestor, fgsenha = await _criar_usuario(async_db, tipo='Funcionario')
    await _associar(async_db, func_gestor.id, c.centro_custo, 'Gestor')
    solicitante, ssenha = await _criar_usuario(async_db)
    fgtoken = await _login(async_client, func_gestor.email, fgsenha)
    stoken = await _login(async_client, solicitante.email, ssenha)

    sol_resp = await _solicitar_entrada(async_client, stoken, c.centro_custo)
    sol_id = sol_resp.json()['id']

    resp = await async_client.put(
        f'{URL}/{sol_id}/aprovar',
        headers={'Authorization': f'Bearer {fgtoken}'},
    )

    assert resp.status_code == HTTPStatus.OK


@pytest.mark.asyncio
@pytest.mark.routers
async def test_gestor_global_com_ocupacao_funcionario_nao_pode_aprovar(
    async_client, async_db
):
    """
    OCP: tipo global 'Gestor' + ocupação 'Funcionario' no CC
    NÃO deve permitir aprovar — tipo global não é critério.
    """
    c = await _criar_contrato(async_db)
    gestor_global, ggsenha = await _criar_usuario(async_db, tipo='Gestor')
    await _associar(async_db, gestor_global.id, c.centro_custo, 'Funcionario')
    gestor_real, grsenha = await _criar_usuario(async_db, tipo='Gestor')
    await _associar(async_db, gestor_real.id, c.centro_custo, 'Gestor')
    solicitante, ssenha = await _criar_usuario(async_db)
    ggtoken = await _login(async_client, gestor_global.email, ggsenha)
    stoken = await _login(async_client, solicitante.email, ssenha)

    sol_resp = await _solicitar_entrada(async_client, stoken, c.centro_custo)
    sol_id = sol_resp.json()['id']

    resp = await async_client.put(
        f'{URL}/{sol_id}/aprovar',
        headers={'Authorization': f'Bearer {ggtoken}'},
    )

    assert resp.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
@pytest.mark.routers
async def test_gestor_de_cc_a_nao_pode_aprovar_solicitacao_de_cc_b(
    async_client, async_db
):
    """
    OCP: permissão é verificada no CC específico da solicitação.
    Gestor do CC A não pode aprovar solicitação do CC B.
    """
    c_a = await _criar_contrato(async_db)
    c_b = await _criar_contrato(async_db)
    gestor, gsenha = await _criar_usuario(async_db, tipo='Gestor')
    await _associar(async_db, gestor.id, c_a.centro_custo, 'Gestor')
    gestor_b, gbsenha = await _criar_usuario(async_db, tipo='Gestor')
    await _associar(async_db, gestor_b.id, c_b.centro_custo, 'Gestor')
    solicitante, ssenha = await _criar_usuario(async_db)
    gtoken = await _login(async_client, gestor.email, gsenha)
    stoken = await _login(async_client, solicitante.email, ssenha)

    sol_resp = await _solicitar_entrada(async_client, stoken, c_b.centro_custo)
    sol_id = sol_resp.json()['id']

    resp = await async_client.put(
        f'{URL}/{sol_id}/aprovar',
        headers={'Authorization': f'Bearer {gtoken}'},
    )

    assert resp.status_code == HTTPStatus.FORBIDDEN


# ─── rejeitar ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_rejeitar_entrada_cc(async_client, async_db):
    c = await _criar_contrato(async_db)
    gestor, gsenha = await _criar_usuario(async_db, 'Gestor')
    await _associar(async_db, gestor.id, c.centro_custo, 'Gestor')
    func, fsenha = await _criar_usuario(async_db)
    gtoken = await _login(async_client, gestor.email, gsenha)
    ftoken = await _login(async_client, func.email, fsenha)

    sol_resp = await _solicitar_entrada(async_client, ftoken, c.centro_custo)
    sol_id = sol_resp.json()['id']

    resp = await async_client.put(
        f'{URL}/{sol_id}/rejeitar',
        headers={'Authorization': f'Bearer {gtoken}'},
    )

    assert resp.status_code == HTTPStatus.OK
    assert resp.json()['status'] == 'rejeitada'


@pytest.mark.asyncio
@pytest.mark.routers
async def test_rejeitar_nao_pendente_retorna_bad_request(
    async_client, async_db
):
    c = await _criar_contrato(async_db)
    gestor, gsenha = await _criar_usuario(async_db, 'Gestor')
    await _associar(async_db, gestor.id, c.centro_custo, 'Gestor')
    func, fsenha = await _criar_usuario(async_db)
    gtoken = await _login(async_client, gestor.email, gsenha)
    ftoken = await _login(async_client, func.email, fsenha)

    sol_resp = await _solicitar_entrada(async_client, ftoken, c.centro_custo)
    sol_id = sol_resp.json()['id']

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
async def test_cancelar_proprio(async_client, async_db):
    c = await _criar_contrato(async_db)
    func, fsenha = await _criar_usuario(async_db)
    ftoken = await _login(async_client, func.email, fsenha)

    sol_resp = await _solicitar_entrada(async_client, ftoken, c.centro_custo)
    sol_id = sol_resp.json()['id']

    resp = await async_client.delete(
        f'{URL}/{sol_id}',
        headers={'Authorization': f'Bearer {ftoken}'},
    )

    assert resp.status_code == HTTPStatus.OK


@pytest.mark.asyncio
@pytest.mark.routers
async def test_cancelar_de_outro_usuario_proibido(async_client, async_db):
    c = await _criar_contrato(async_db)
    func, fsenha = await _criar_usuario(async_db)
    outro, osenha = await _criar_usuario(async_db)
    ftoken = await _login(async_client, func.email, fsenha)
    otoken = await _login(async_client, outro.email, osenha)

    sol_resp = await _solicitar_entrada(async_client, ftoken, c.centro_custo)
    sol_id = sol_resp.json()['id']

    resp = await async_client.delete(
        f'{URL}/{sol_id}',
        headers={'Authorization': f'Bearer {otoken}'},
    )

    assert resp.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
@pytest.mark.routers
async def test_cancelar_nao_encontrado(async_client, login_teste):
    resp = await async_client.delete(
        f'{URL}/9999',
        headers={'Authorization': f'Bearer {login_teste["token"]}'},
    )

    assert resp.status_code == HTTPStatus.NOT_FOUND


# ─── get ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.routers
async def test_get_usuario_ve_proprias_solicitacoes(async_client, async_db):
    c = await _criar_contrato(async_db)
    func, fsenha = await _criar_usuario(async_db)
    ftoken = await _login(async_client, func.email, fsenha)

    await _solicitar_entrada(async_client, ftoken, c.centro_custo)

    resp = await async_client.get(
        f'{URL}/',
        headers={'Authorization': f'Bearer {ftoken}'},
    )

    assert resp.status_code == HTTPStatus.OK
    assert len(resp.json()['solicitacoes']) == 1


@pytest.mark.asyncio
@pytest.mark.routers
async def test_gestor_ve_pedidos_do_seu_cc(async_client, async_db):
    c = await _criar_contrato(async_db)
    gestor, gsenha = await _criar_usuario(async_db, 'Gestor')
    await _associar(async_db, gestor.id, c.centro_custo, 'Gestor')
    func, fsenha = await _criar_usuario(async_db)
    gtoken = await _login(async_client, gestor.email, gsenha)
    ftoken = await _login(async_client, func.email, fsenha)

    await _solicitar_entrada(
        async_client, ftoken, c.centro_custo, ocupacao='Subgestor'
    )

    resp = await async_client.get(
        f'{URL}/',
        headers={'Authorization': f'Bearer {gtoken}'},
    )

    solicitacoes = resp.json()['solicitacoes']
    assert any(s['solicitante_id'] == func.id for s in solicitacoes)


@pytest.mark.asyncio
@pytest.mark.routers
async def test_subgestor_nao_ve_solicitacao_de_cargo_maior(
    async_client, async_db
):
    c = await _criar_contrato(async_db)
    subg, ssenha = await _criar_usuario(async_db, 'Subgestor')
    await _associar(async_db, subg.id, c.centro_custo, 'Subgestor')
    func, fsenha = await _criar_usuario(async_db)
    stoken = await _login(async_client, subg.email, ssenha)
    ftoken = await _login(async_client, func.email, fsenha)

    await _solicitar_entrada(
        async_client, ftoken, c.centro_custo, ocupacao='Gestor'
    )

    resp = await async_client.get(
        f'{URL}/',
        headers={'Authorization': f'Bearer {stoken}'},
    )

    solicitacoes = resp.json()['solicitacoes']
    assert not any(s['solicitante_id'] == func.id for s in solicitacoes)


@pytest.mark.asyncio
@pytest.mark.routers
async def test_subgestor_ve_solicitacao_de_funcionario(async_client, async_db):
    c = await _criar_contrato(async_db)
    subg, ssenha = await _criar_usuario(async_db, 'Subgestor')
    await _associar(async_db, subg.id, c.centro_custo, 'Subgestor')
    func, fsenha = await _criar_usuario(async_db)
    stoken = await _login(async_client, subg.email, ssenha)
    ftoken = await _login(async_client, func.email, fsenha)

    await _solicitar_entrada(async_client, ftoken, c.centro_custo)

    resp = await async_client.get(
        f'{URL}/',
        headers={'Authorization': f'Bearer {stoken}'},
    )

    solicitacoes = resp.json()['solicitacoes']
    assert any(s['solicitante_id'] == func.id for s in solicitacoes)
