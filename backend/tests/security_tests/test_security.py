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
async def test_get_current_user_invalid_token():
    with pytest.raises(HTTPException) as exc_info:
        await Dependencies.get_current_user(token='invalid_token')

    assert exc_info.value.status_code == HTTPStatus.UNAUTHORIZED
    assert exc_info.value.detail == 'Credenciais inválidas.'
