"""Autenticação via Keycloak: validação do token, gate de grupo e provisionamento.

Substitui os testes de hashing de senha, de HS256 e de `role_required` — os três
deixaram de existir com o SSO. Cada teste aqui cobre uma maneira de o desenho
falhar em silêncio.
"""

from http import HTTPStatus

import pytest
from sqlalchemy import func, select

from backend.model.user import User
from tests.support import oidc


URL = '/users/'
SUB = 'aaaaaaaa-0000-0000-0000-000000000001'


async def _quantos_usuarios(db) -> int:
    return (await db.execute(select(func.count()).select_from(User))).scalar_one()


def _cabecalhos(token: str) -> dict[str, str]:
    return {'Authorization': f'Bearer {token}'}


@pytest.mark.asyncio
@pytest.mark.security
async def test_sem_o_grupo_recebe_403_e_nao_e_provisionado(
    async_client, async_db
):
    """A checagem que impede o provisionamento de abrir o sistema ao realm todo.

    Sem ela, qualquer pessoa autenticada no Keycloak — inclusive quem só usa a
    receita — entraria no inventário e ainda ganharia uma linha em tb_users. O
    portal esconde o cartão, mas quem digitar a URL chega aqui.
    """
    antes = await _quantos_usuarios(async_db)

    token = oidc.cunhar_token(
        SUB, 'so.receita@ufc.com.br', groups=['/apps/receita']
    )
    resposta = await async_client.get(URL, headers=_cabecalhos(token))

    assert resposta.status_code == HTTPStatus.FORBIDDEN
    assert await _quantos_usuarios(async_db) == antes


@pytest.mark.asyncio
@pytest.mark.security
async def test_sem_nenhum_grupo_recebe_403(async_client):
    token = oidc.cunhar_token(SUB, 'ninguem@ufc.com.br', groups=[])
    resposta = await async_client.get(URL, headers=_cabecalhos(token))
    assert resposta.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
@pytest.mark.security
async def test_emissor_diferente_e_recusado(async_client):
    token = oidc.cunhar_token(
        SUB, 'alguem@ufc.com.br', issuer='http://outro-keycloak/realms/x'
    )
    resposta = await async_client.get(URL, headers=_cabecalhos(token))
    assert resposta.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.asyncio
@pytest.mark.security
async def test_audiencia_diferente_e_recusada(async_client):
    """Um token válido da despesa não vale para o inventário."""
    token = oidc.cunhar_token(SUB, 'alguem@ufc.com.br', audience='despesa-api')
    resposta = await async_client.get(URL, headers=_cabecalhos(token))
    assert resposta.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.asyncio
@pytest.mark.security
async def test_token_expirado_e_recusado(async_client):
    token = oidc.cunhar_token(SUB, 'alguem@ufc.com.br', expirado=True)
    resposta = await async_client.get(URL, headers=_cabecalhos(token))
    assert resposta.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.asyncio
@pytest.mark.security
async def test_token_sem_assinatura_valida_e_recusado(async_client):
    resposta = await async_client.get(URL, headers=_cabecalhos('nao.e.token'))
    assert resposta.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.asyncio
@pytest.mark.security
async def test_sem_token_recebe_401(async_client):
    resposta = await async_client.get(URL)
    assert resposta.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.asyncio
@pytest.mark.security
async def test_primeiro_acesso_provisiona_como_funcionario(
    async_client, async_db
):
    """Grupo é acesso, `tipo` é papel — um não se infere do outro.

    Quem chega pelo SSO entra como Funcionario (o mesmo que o auto-registro já
    forçava) e um Admin promove depois. `tb_users.tipo` tem CheckConstraint e
    nenhum default, então o valor precisa ser explícito.
    """
    email = 'novo@ufc.com.br'
    token = oidc.cunhar_token(SUB, email, nome='Fulano da Silva')

    resposta = await async_client.get(URL, headers=_cabecalhos(token))
    assert resposta.status_code == HTTPStatus.OK

    criado = (
        await async_db.execute(select(User).where(User.email == email))
    ).scalar_one()
    assert criado.external_id == SUB
    assert criado.tipo == 'Funcionario'
    assert criado.nome == 'Fulano da Silva'
    assert criado.senha is None


@pytest.mark.asyncio
@pytest.mark.security
async def test_conta_anterior_ao_sso_e_reaproveitada_pelo_email(
    async_client, async_db
):
    """O ponto que preserva as FKs.

    Quem já tinha conta precisa continuar com o MESMO id — há eletrônicos,
    cessões, solicitações, associações de centro de custo e registros de
    auditoria apontando para ele. O casamento por email acontece uma vez; daí em
    diante é pelo external_id.

    Preserva também o `tipo`: um Admin que já existia não é rebaixado.
    """
    antigo = User(
        nome='ja existia',
        email='antigo@ufc.com.br',
        senha='$argon2$hash-legado',
        tipo='Admin',
    )
    async_db.add(antigo)
    await async_db.commit()
    await async_db.refresh(antigo)
    id_original = antigo.id

    token = oidc.cunhar_token(SUB, 'antigo@ufc.com.br')
    resposta = await async_client.get(URL, headers=_cabecalhos(token))
    assert resposta.status_code == HTTPStatus.OK

    depois = (
        await async_db.execute(
            select(User).where(User.email == 'antigo@ufc.com.br')
        )
    ).scalar_one()
    assert depois.id == id_original
    assert depois.external_id == SUB
    assert depois.tipo == 'Admin'
    assert await _quantos_usuarios(async_db) == 1


@pytest.mark.asyncio
@pytest.mark.security
async def test_external_id_tem_precedencia_sobre_o_email(
    async_client, async_db
):
    """Depois de vinculado, trocar o email no Keycloak não cria conta nova."""
    user = User(
        nome='vinculado',
        email='antes@ufc.com.br',
        tipo='Funcionario',
        external_id=SUB,
    )
    async_db.add(user)
    await async_db.commit()

    token = oidc.cunhar_token(SUB, 'depois@ufc.com.br')
    resposta = await async_client.get(URL, headers=_cabecalhos(token))

    assert resposta.status_code == HTTPStatus.OK
    assert await _quantos_usuarios(async_db) == 1


@pytest.mark.asyncio
@pytest.mark.security
async def test_perder_o_grupo_barra_sem_apagar_e_sem_rebaixar(
    async_client, async_db
):
    """Tirar do grupo barra o acesso; a conta e o PAPEL continuam intactos.

    Há eletrônicos, cessões, solicitações, associações de centro de custo e
    auditoria apontando para a linha. E `tipo` é papel, não acesso: quem for
    readmitido volta como era, sem precisar ser promovido de novo.
    """
    admin = User(
        nome='Chefe', email='chefe@ufc.com.br', tipo='Admin', external_id=SUB
    )
    async_db.add(admin)
    await async_db.commit()
    id_original = admin.id

    # Sem o grupo: barrado.
    resposta = await async_client.get(
        URL, headers=_cabecalhos(oidc.cunhar_token(SUB, 'chefe@ufc.com.br', groups=[]))
    )
    assert resposta.status_code == HTTPStatus.FORBIDDEN

    # De volta ao grupo: mesma linha, mesmo papel.
    resposta = await async_client.get(
        URL, headers=_cabecalhos(oidc.cunhar_token(SUB, 'chefe@ufc.com.br'))
    )
    assert resposta.status_code == HTTPStatus.OK

    depois = (
        await async_db.execute(select(User).where(User.email == 'chefe@ufc.com.br'))
    ).scalar_one()
    assert depois.id == id_original, 'a conta não pode ser recriada'
    assert depois.tipo == 'Admin', 'perder o acesso não pode rebaixar o papel'
    assert depois.ativo is True


@pytest.mark.asyncio
@pytest.mark.security
async def test_sem_grupo_nao_provisiona_nem_marca_ninguem(async_client, async_db):
    """Quem nunca entrou e chega sem o grupo não vira linha no banco."""
    antes = await _quantos_usuarios(async_db)
    resposta = await async_client.get(
        URL, headers=_cabecalhos(oidc.cunhar_token(SUB, 'estranho@ufc.com.br', groups=[]))
    )
    assert resposta.status_code == HTTPStatus.FORBIDDEN
    assert await _quantos_usuarios(async_db) == antes
