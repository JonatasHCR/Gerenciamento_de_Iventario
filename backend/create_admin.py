"""
Garante que alguém tenha o papel de Admin no inventário.

Com o SSO, este script deixou de criar senha: quem guarda credencial é o
Keycloak. O que ele faz é o outro lado da moeda — o **papel** dentro do sistema,
que continua local (`tb_users.tipo`).

A pessoa precisa existir nos DOIS lugares:

  1. no Keycloak, no grupo `/apps/inventario`  → decide se ela PODE ENTRAR
  2. aqui, com tipo='Admin'                    → decide o que ela PODE FAZER

Este script cuida do item 2. O vínculo entre os dois é feito sozinho no primeiro
login, casando por email e gravando o `external_id`.

Uso, a partir da pasta backend/:
    python create_admin.py                      # usa o email padrão
    python create_admin.py fulano@ufc.com.br    # promove/cria outro
"""

import asyncio
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.settings import Settings
from backend.model.user import User

ADMIN_NOME = 'Administrador'
ADMIN_EMAIL = 'admin@admin.com'
ADMIN_TIPO = 'Admin'


async def garantir_admin(session: AsyncSession, email: str) -> None:
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(nome=ADMIN_NOME, email=email, tipo=ADMIN_TIPO)
        session.add(user)
        acao = 'criado'
    elif user.tipo == ADMIN_TIPO:
        print(f'{email} já é Admin. Nada a fazer.')
        return
    else:
        print(f'{email} existe como {user.tipo}; promovendo a Admin.')
        user.tipo = ADMIN_TIPO
        acao = 'promovido'

    await session.commit()

    print(f'Usuário {acao} como Admin: {email}')
    print()
    print('Falta o outro lado: no Keycloak, confira que este email existe no')
    print('realm `ufc` e pertence ao grupo /apps/inventario. Sem isso a pessoa')
    print('não consegue entrar — o papel local só vale depois de autenticar.')


async def main() -> None:
    email = sys.argv[1].strip().lower() if len(sys.argv) > 1 else ADMIN_EMAIL

    settings = Settings()
    engine = create_async_engine(settings.database_url_async())
    SessionLocal = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    async with SessionLocal() as session:
        await garantir_admin(session, email)

    await engine.dispose()


if __name__ == '__main__':
    asyncio.run(main())
