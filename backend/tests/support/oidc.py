"""Keycloak de mentira para os testes.

Gera um par de chaves RSA no início da sessão e cunha tokens assinados com ele.
O `PyJWKClient` real é substituído por um que devolve essa chave, então
`get_current_user` roda o caminho de produção inteiro — assinatura RS256,
`issuer`, `audience` e a claim `groups` — sem rede e sem Keycloak no ar.

O que NÃO é simulado é de propósito: se a validação parar de checar audiência
ou grupo, os testes daqui a pouco reprovam.
"""

from __future__ import annotations

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

# O mesmo issuer configurado no conftest.
ISSUER = "http://keycloak-de-teste:8080/realms/ufc"
AUDIENCE = "inventario-api"
GRUPO = "/apps/inventario"

_CHAVE = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_PRIVADA = _CHAVE
_PUBLICA = _CHAVE.public_key()


class _ChaveDeAssinatura:
    """Imita o objeto que o PyJWKClient devolve — só a chave interessa."""

    def __init__(self, key):
        self.key = key


class JWKClientFalso:
    """Substitui o `jwt.PyJWKClient` sem tocar na rede."""

    def __init__(self, *_args, **_kwargs):
        pass

    def get_signing_key_from_jwt(self, _token: str) -> _ChaveDeAssinatura:
        return _ChaveDeAssinatura(_PUBLICA)


def cunhar_token(
    sub: str,
    email: str,
    nome: str = "Usuario Teste",
    groups: list[str] | None = None,
    issuer: str = ISSUER,
    audience: str = AUDIENCE,
    expirado: bool = False,
) -> str:
    """Cunha um access token como o Keycloak emitiria.

    Os parâmetros existem para os testes negativos: emissor errado, audiência
    errada, sem o grupo, expirado.
    """
    import time

    agora = int(time.time())
    payload = {
        "iss": issuer,
        "aud": [audience, "account"],  # o Keycloak sempre inclui "account"
        "sub": sub,
        "email": email,
        "name": nome,
        "preferred_username": email,
        "groups": [GRUPO] if groups is None else groups,
        "iat": agora - 10,
        "exp": agora - 5 if expirado else agora + 3600,
    }
    return jwt.encode(payload, _PRIVADA, algorithm="RS256")


def cabecalhos(**kwargs) -> dict[str, str]:
    return {"Authorization": f"Bearer {cunhar_token(**kwargs)}"}


def token_de(user, **kwargs) -> str:
    """Token para uma linha `User` já existente no banco de teste.

    Usa o `external_id` se houver; senão o email, que é como o primeiro login
    de quem já tinha conta acontece na vida real.
    """
    return cunhar_token(
        sub=getattr(user, "external_id", None) or f"sub-{user.email}",
        email=user.email,
        nome=user.nome,
        **kwargs,
    )
