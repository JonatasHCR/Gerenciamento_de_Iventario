"""
Tests da restrição de domínio no auto-registro (POST /users/).
A restrição é configurável via env ALLOWED_EMAIL_DOMAINS.
"""

from http import HTTPStatus
from unittest.mock import patch

import pytest

from backend.core.settings import Settings


def _settings_mock(domains: str):
    """Faz Settings().ALLOWED_EMAIL_DOMAINS retornar o que queremos."""

    class _M(Settings):
        ALLOWED_EMAIL_DOMAINS: str = domains  # type: ignore[misc]

    return _M


@pytest.mark.asyncio
@pytest.mark.routers
async def test_autoregistro_sem_restricao(async_client):
    """Sem ALLOWED_EMAIL_DOMAINS configurado, qualquer email passa."""
    with patch('backend.service.user.Settings', _settings_mock('')):
        resp = await async_client.post(
            '/users/',
            json={
                'nome': 'AnyDomain',
                'email': 'anyone@qualquer.com',
                'senha': 'senha123',
                'tipo': 'Funcionario',
            },
        )
    assert resp.status_code == HTTPStatus.CREATED


@pytest.mark.asyncio
@pytest.mark.routers
async def test_autoregistro_dominio_permitido(async_client):
    """Email em domínio permitido passa."""
    with patch(
        'backend.service.user.Settings',
        _settings_mock('ufcengenharia.com.br,sememail.com'),
    ):
        resp = await async_client.post(
            '/users/',
            json={
                'nome': 'UfcUser',
                'email': 'fulano@ufcengenharia.com.br',
                'senha': 'senha123',
                'tipo': 'Funcionario',
            },
        )
    assert resp.status_code == HTTPStatus.CREATED


@pytest.mark.asyncio
@pytest.mark.routers
async def test_autoregistro_dominio_fallback(async_client):
    """Email com domínio @sememail.com (fallback) passa."""
    with patch(
        'backend.service.user.Settings',
        _settings_mock('ufcengenharia.com.br,sememail.com'),
    ):
        resp = await async_client.post(
            '/users/',
            json={
                'nome': 'SemEmail',
                'email': 'fulano@sememail.com',
                'senha': 'senha123',
                'tipo': 'Funcionario',
            },
        )
    assert resp.status_code == HTTPStatus.CREATED


@pytest.mark.asyncio
@pytest.mark.routers
async def test_autoregistro_dominio_proibido(async_client):
    """Email em domínio não-permitido recebe 403."""
    with patch(
        'backend.service.user.Settings',
        _settings_mock('ufcengenharia.com.br,sememail.com'),
    ):
        resp = await async_client.post(
            '/users/',
            json={
                'nome': 'Outsider',
                'email': 'fulano@dominioqualquer.com',
                'senha': 'senha123',
                'tipo': 'Funcionario',
            },
        )
    assert resp.status_code == HTTPStatus.FORBIDDEN
    assert 'ufcengenharia.com.br' in resp.json()['detail']


@pytest.mark.asyncio
@pytest.mark.routers
async def test_autoregistro_dominio_case_insensitive(async_client):
    """Match de domínio é case-insensitive."""
    with patch(
        'backend.service.user.Settings',
        _settings_mock('ufcengenharia.com.br'),
    ):
        resp = await async_client.post(
            '/users/',
            json={
                'nome': 'CaseUser',
                'email': 'fulano@UfcEngenharia.com.BR',
                'senha': 'senha123',
                'tipo': 'Funcionario',
            },
        )
    assert resp.status_code == HTTPStatus.CREATED


@pytest.mark.asyncio
@pytest.mark.routers
async def test_admin_criacao_ignora_restricao(async_client, login_teste):
    """POST /users/admin não passa pela validação de domínio."""
    with patch(
        'backend.service.user.Settings',
        _settings_mock('apenas.com'),
    ):
        resp = await async_client.post(
            '/users/admin',
            json={
                'nome': 'AdminCreated',
                'email': 'criado_por_admin@outro.com',
                'senha': 'senha123',
                'tipo': 'Gestor',
            },
            headers={'Authorization': f'Bearer {login_teste["token"]}'},
        )
    assert resp.status_code == HTTPStatus.CREATED
