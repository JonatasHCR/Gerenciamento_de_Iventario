from dataclasses import dataclass, field
from http import HTTPStatus
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2AuthorizationCodeBearer
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.engine import EngineApp
from backend.core.settings import Settings
from backend.model.associacao_user_contrato import AssociacaoUserContrato
from backend.model.user import User

T_AsyncSession = Annotated[AsyncSession, Depends(EngineApp.get_async_session)]

_settings = Settings()
_PRIVILEGED = frozenset({'Admin'})

# Só documenta o fluxo no Swagger: quem emite o token é o Keycloak. O front
# fala com o proxy do Next, que anexa o header a partir do cookie.
T_OAuth2bearer = Annotated[
    str,
    Depends(
        OAuth2AuthorizationCodeBearer(
            authorizationUrl=_settings.oidc_authorization_url,
            tokenUrl=_settings.oidc_token_url,
        )
    ),
]

# Preguiçoso: nada é baixado no import, só na primeira validação.
_jwks_client = jwt.PyJWKClient(_settings.oidc_jwks_url)

# `tb_users.tipo` tem CheckConstraint e nenhum default: precisa ser explícito.
# Um Admin promove depois.
TIPO_PADRAO = 'Funcionario'


@dataclass
class UserContext:
    """Contexto do usuário autenticado com seus centros de custo resolvidos."""

    user: User
    centros_custo: list[str] = field(default_factory=list)
    # { centro_custo: ocupacao } — ex: {'CC001': 'Gestor'}
    ocupacoes: dict[str, str] = field(default_factory=dict)

    @property
    def is_privileged(self) -> bool:
        """Admin — acesso irrestrito a tudo."""
        return self.user.tipo in _PRIVILEGED

    @property
    def is_tecnico_ti(self) -> bool:
        """Tecnico_TI — eletrônicos sem restrição; demais: só leitura."""
        return self.user.tipo == 'Tecnico_TI'

    def assert_cc(self, centro_custo: str) -> None:
        """Lança 403 se o CC não pertence ao usuário (exceto privilegiados)."""
        if not self.is_privileged and centro_custo not in self.centros_custo:
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail='Sem permissão para operar neste centro de custo.',
            )

    def assert_write(self, *allowed_tipos: str) -> None:
        """Lança 403 se o tipo do usuário não está na lista de permitidos."""
        if not self.is_privileged and self.user.tipo not in set(allowed_tipos):
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail='Sem permissão para esta operação.',
            )

    def ocupacao_in(self, centro_custo: str) -> str | None:
        """Retorna a ocupação do usuário neste CC, ou None se não pertence."""
        return self.ocupacoes.get(centro_custo)

    def assert_cc_role(
        self, centro_custo: str, *roles: str
    ) -> None:
        """403 salvo se Admin, ou se a ocupação neste CC estiver em `roles`.

        Olha a ocupação no CC, não o tipo global; Tecnico_TI não passa aqui.
        """
        if self.is_privileged:
            return
        if self.ocupacoes.get(centro_custo) in set(roles):
            return
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail='Sem permissão neste centro de custo.',
        )


def _e_mestre(email: str) -> bool:
    """A conta mestra: um único email, vindo do infra/.env.

    Não é grupo nem papel do Keycloak — ser admin do console não dá poder algum
    aqui. É só este endereço, Admin dos três sistemas ao mesmo tempo.
    """
    mestre = (_settings.ADMIN_MESTRE_EMAIL or '').strip().lower()
    return bool(mestre) and email == mestre


def _sem_acesso() -> HTTPException:
    return HTTPException(
        status_code=HTTPStatus.FORBIDDEN,
        detail='Você não tem acesso ao inventário. '
        'Peça a liberação ao administrador.',
    )


class Dependencies:
    @staticmethod
    async def get_current_user(
        token: T_OAuth2bearer,
        session: T_AsyncSession,
    ) -> User:
        """Valida o token do Keycloak e devolve o usuário local correspondente.

        Resolve por `external_id`, caindo para o email na primeira vez — o que
        grava o vínculo e preserva o id, e com ele todas as FKs.
        """
        credentials_error = HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail='Credenciais inválidas.',
            headers={'WWW-Authenticate': 'Bearer'},
        )

        try:
            chave = _jwks_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                chave.key,
                algorithms=['RS256'],
                issuer=_settings.OIDC_ISSUER,
                audience=_settings.OIDC_AUDIENCE,
            )
        except (jwt.PyJWTError, jwt.PyJWKClientError):
            raise credentials_error

        sub = payload.get('sub')
        email = (payload.get('email') or '').strip().lower()
        if not sub or not email:
            raise credentials_error

        # A mestra entra sem grupo: se dependesse, tirar a si mesmo de um grupo
        # trancaria a porta de quem conserta.
        mestre = _e_mestre(email)
        tem_acesso = mestre or (
            _settings.OIDC_REQUIRED_GROUP in (payload.get('groups') or [])
        )

        # 1) já vinculado — o caminho normal, depois do primeiro login
        result = await session.execute(
            select(User).where(User.external_id == sub)
        )
        user = result.scalar_one_or_none()

        # 2) conta anterior ao SSO: casa por email e grava o vínculo
        if user is None:
            result = await session.execute(
                select(User).where(User.email == email)
            )
            user = result.scalar_one_or_none()
            if user is not None:
                user.external_id = sub

        if user is not None:
            # Espelha o acesso do Keycloak. Nunca apagada: há eletrônicos,
            # cessões e auditoria apontando para ela. Perder o grupo não rebaixa
            # o `tipo` — a exceção é a conta mestra, logo abaixo.
            if user.ativo != tem_acesso:
                user.ativo = tem_acesso

            # A cada login, para trocar o ADMIN_MESTRE_EMAIL valer sem script.
            if mestre and user.tipo != 'Admin':
                user.tipo = 'Admin'

            await session.commit()
            await session.refresh(user)

            if not tem_acesso:
                raise _sem_acesso()
            return user

        # 3) primeira vez no sistema (JIT). Sem o grupo, NÃO provisiona: o
        #    cadastro não pode ser efeito colateral de um acesso negado.
        if not tem_acesso:
            raise _sem_acesso()

        #    Grupo é acesso, `tipo` é papel: não dá para inferir um do outro.
        #    A mestra é a exceção, e vem do .env, não do token.
        novo = User(
            nome=(payload.get('name') or email).strip(),
            email=email,
            tipo='Admin' if mestre else TIPO_PADRAO,
            external_id=sub,
        )
        session.add(novo)
        try:
            await session.commit()
        except IntegrityError:
            # Corrida entre duas requisições do mesmo usuário recém-chegado.
            await session.rollback()
            result = await session.execute(
                select(User).where(User.external_id == sub)
            )
            existente = result.scalar_one_or_none()
            if existente is None:
                raise
            return existente
        await session.refresh(novo)
        return novo

    @staticmethod
    async def get_user_context(
        user: Annotated[User, Depends(get_current_user)],
        session: T_AsyncSession,
    ) -> UserContext:
        result = await session.execute(
            select(
                AssociacaoUserContrato.centro_custo,
                AssociacaoUserContrato.ocupacao,
            ).where(AssociacaoUserContrato.user_id == user.id)
        )
        rows = result.all()
        centros_custo = [r.centro_custo for r in rows]
        ocupacoes = {r.centro_custo: r.ocupacao for r in rows}
        return UserContext(
            user=user, centros_custo=centros_custo, ocupacoes=ocupacoes
        )
