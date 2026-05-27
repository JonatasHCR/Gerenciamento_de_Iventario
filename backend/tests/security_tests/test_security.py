from http import HTTPStatus

import pytest
from fastapi import HTTPException
from jwt import decode

from backend.security.dependencies import Dependencies
from backend.security.security import Security


@pytest.mark.security
def test_password_hashing():
    security = Security()
    senha = 'minha_senha_secreta'
    hashed_senha = security.get_senha_hash(senha)

    assert hashed_senha != senha
    assert security.verify_senha(senha, hashed_senha)


@pytest.mark.security
def test_password_verification():
    security = Security()
    senha = 'outra_senha_secreta'
    hashed_senha = security.get_senha_hash(senha)

    assert security.verify_senha(senha, hashed_senha)
    assert not security.verify_senha('senha_errada', hashed_senha)


@pytest.mark.security
def test_access_token_generation():
    security = Security()
    data = {'sub': 'user_id'}
    token = security.get_access_token(data)

    decoded_data = decode(
        token,
        security.settings.SECRET_KEY,
        algorithms=[security.settings.ALGORITHM],
    )

    assert isinstance(token, str)
    assert decoded_data['sub'] == 'user_id'
    assert 'exp' in decoded_data


@pytest.mark.security
@pytest.mark.asyncio
async def test_role_required_dependency():
    class FakeUser:
        tipo = 'Admin'

    dependency = Dependencies.role_required('Admin')

    result = await dependency(current_user=FakeUser())

    assert result.tipo == 'Admin'


@pytest.mark.security
@pytest.mark.asyncio
async def test_role_required_dependency_forbidden():
    class FakeUser:
        tipo = 'Funcionario'

    dependency = Dependencies.role_required('Admin')

    with pytest.raises(HTTPException) as exc_info:
        await dependency(current_user=FakeUser())

    assert exc_info.value.status_code == HTTPStatus.FORBIDDEN
    assert exc_info.value.detail == 'Sem permissão'


@pytest.mark.security
@pytest.mark.asyncio
async def test_get_current_user_invalid_token(async_db):
    with pytest.raises(HTTPException) as exc_info:
        await Dependencies.get_current_user(
            token='invalid_token', session=async_db
        )

    assert exc_info.value.status_code == HTTPStatus.UNAUTHORIZED
    assert exc_info.value.detail == 'Credenciais inválidas.'


@pytest.mark.security
@pytest.mark.asyncio
async def test_get_current_user_no_email_in_token(async_db):
    token = Security().get_access_token({'sub': ''})

    with pytest.raises(HTTPException) as exc_info:
        await Dependencies.get_current_user(token=token, session=async_db)

    assert exc_info.value.status_code == HTTPStatus.UNAUTHORIZED
    assert exc_info.value.detail == 'Credenciais inválidas.'


@pytest.mark.security
@pytest.mark.asyncio
async def test_get_current_user_no_user_in_token(async_db):
    token = Security().get_access_token({'sub': 'no@email.com'})

    with pytest.raises(HTTPException) as exc_info:
        await Dependencies.get_current_user(token=token, session=async_db)

    assert exc_info.value.status_code == HTTPStatus.UNAUTHORIZED
    assert exc_info.value.detail == 'Credenciais inválidas.'


# ─── DIP: Security instancia Settings diretamente (sem injeção) ──────────


@pytest.mark.security
def test_security_acoplado_diretamente_a_settings():
    """
    DIP: Security() cria Settings internamente em vez de recebê-lo como
    parâmetro. Não é possível injetar uma configuração alternativa (ex:
    SECRET_KEY de testes) sem subclassificar Security. O atributo
    `settings` é acessível, mas criado pelo próprio construtor.
    """
    s = Security()
    assert hasattr(s, 'settings')
    assert s.settings.SECRET_KEY  # lido diretamente, sem injeção
    assert s.settings.ALGORITHM


@pytest.mark.security
def test_duas_instancias_security_compartilham_mesma_chave():
    """
    DIP (consequência): duas instâncias de Security independentes usam a
    mesma chave porque ambas leem do mesmo Settings estático. Um token
    gerado por uma é verificável pela outra — acoplamento implícito.
    """
    s1 = Security()
    s2 = Security()
    token = s1.get_access_token({'sub': 'dip@test.com'})
    decoded = decode(
        token,
        s2.settings.SECRET_KEY,
        algorithms=[s2.settings.ALGORITHM],
    )
    assert decoded['sub'] == 'dip@test.com'
