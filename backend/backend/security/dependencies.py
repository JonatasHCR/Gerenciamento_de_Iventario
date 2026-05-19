from dataclasses import dataclass, field
from http import HTTPStatus
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jwt import DecodeError, ExpiredSignatureError, decode
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.engine import EngineApp
from backend.core.settings import Settings
from backend.model.associacao_user_contrato import AssociacaoUserContrato
from backend.model.user import User

T_AsyncSession = Annotated[AsyncSession, Depends(EngineApp.get_async_session)]
T_OAuth2bearer = Annotated[
    str, Depends(OAuth2PasswordBearer(tokenUrl='auth/login'))
]

_PRIVILEGED = frozenset({'Admin'})


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
        """
        Lança 403 a menos que:
        - usuário seja privilegiado (Admin), OU
        - sua ocupacao neste CC seja uma das em `roles`.

        Diferente de `assert_write` (que olha o tipo global), este olha
        a ocupação no CC. Tecnico_TI **não** bypassa aqui — quem usa
        este método precisa decidir explicitamente sobre Tecnico_TI.
        """
        if self.is_privileged:
            return
        if self.ocupacoes.get(centro_custo) in set(roles):
            return
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail='Sem permissão neste centro de custo.',
        )


class Dependencies:
    @staticmethod
    async def get_current_user(
        token: T_OAuth2bearer,
        session: T_AsyncSession,
    ) -> User:
        try:
            payload = decode(
                token,
                Settings().SECRET_KEY,
                algorithms=[Settings().ALGORITHM],
            )
        except (DecodeError, ExpiredSignatureError):
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail='Credenciais inválidas.',
                headers={'WWW-Authenticate': 'Bearer'},
            )

        email = payload.get('sub')
        if not email:
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail='Credenciais inválidas.',
            )

        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail='Credenciais inválidas.',
            )

        return user

    @staticmethod
    async def get_user_context(
        user: Annotated[User, Depends(get_current_user)],
        session: T_AsyncSession,
    ) -> UserContext:
        result = await session.execute(
            select(AssociacaoUserContrato).where(
                AssociacaoUserContrato.user_id == user.id
            )
        )
        rows = result.scalars().all()
        centros_custo = [r.centro_custo for r in rows]
        ocupacoes = {r.centro_custo: r.ocupacao for r in rows}
        return UserContext(
            user=user, centros_custo=centros_custo, ocupacoes=ocupacoes
        )

    @staticmethod
    def role_required(*roles: str):
        async def dependency(
            current_user: Annotated[
                User, Depends(Dependencies.get_current_user)
            ],
        ):
            if current_user.tipo not in set(roles):
                raise HTTPException(
                    status_code=HTTPStatus.FORBIDDEN,
                    detail='Sem permissão',
                )
            return current_user

        return dependency
