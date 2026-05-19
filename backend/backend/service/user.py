from http import HTTPStatus

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.settings import Settings
from backend.model.associacao_user_contrato import AssociacaoUserContrato
from backend.model.user import User
from backend.schemas.user import UserCreate, UserUpdate
from backend.security.dependencies import UserContext
from backend.security.security import Security
from backend.service.audit_log import log as audit_log


def _allowed_email_domains() -> set[str]:
    raw = Settings().ALLOWED_EMAIL_DOMAINS
    return {
        d.strip().lower().lstrip('@')
        for d in raw.split(',')
        if d.strip()
    }


class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.security = Security()

    async def get_users(self, ctx: UserContext):
        """
        - Admin/TI → todos os usuários.
        - Gestor/Subgestor → todos os usuários (para poder enviar solicitações)
        - Funcionario → apenas usuários do mesmo CC.
        """
        pode_ver_todos = ctx.is_privileged or ctx.is_tecnico_ti
        if pode_ver_todos or ctx.user.tipo in {'Gestor', 'Subgestor'}:
            result = await self.session.execute(select(User))
            return result.scalars().all()

        # apenas usuários que compartilham pelo menos um CC com ele
        if not ctx.centros_custo:
            return [ctx.user]

        result = await self.session.execute(
            select(User)
            .join(
                AssociacaoUserContrato,
                AssociacaoUserContrato.user_id == User.id,
            )
            .where(AssociacaoUserContrato.centro_custo.in_(ctx.centros_custo))
            .distinct()
        )
        return result.scalars().all()

    async def create(self, user: UserCreate, ctx: UserContext | None = None):
        """
        - cria sempre como Funcionario.
        - Admin/TI → pode criar qualquer tipo.
        - Demais perfis logados → 403.
        """
        if ctx is not None and not ctx.is_privileged:
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail='Apenas Admin pode criar usuários '
                'com tipo específico. Use o auto-registro.',
            )

        # Auto-registro: forçar tipo Funcionario e validar domínio do email
        if ctx is None:
            user = user.model_copy(update={'tipo': 'Funcionario'})

            allowed = _allowed_email_domains()
            if allowed:
                dom = user.email.split('@', 1)[1].lower()
                if dom not in allowed:
                    raise HTTPException(
                        status_code=HTTPStatus.FORBIDDEN,
                        detail=(
                            f'Auto-registro restrito a emails dos '
                            f'domínios: {", ".join(sorted(allowed))}.'
                        ),
                    )

        existing = await self.session.execute(
            select(User).where(User.email == user.email)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail='Usuário com este email já existe.',
            )

        novo = User(**user.model_dump())
        novo.senha = self.security.get_senha_hash(novo.senha)

        self.session.add(novo)
        await self.session.commit()
        await self.session.refresh(novo)
        return novo

    async def update(self, user_id: int, user: UserUpdate, ctx: UserContext):
        """
        - Admin/TI → podem editar qualquer usuário e qualquer campo.
        - Demais → apenas o próprio perfil; não podem alterar o campo `tipo`.
        """
        if not ctx.is_privileged and ctx.user.id != user_id:
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail='Você só pode editar o próprio perfil.',
            )

        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        user_db = result.scalar_one_or_none()
        if user_db is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail='Usuário não encontrado.',
            )

        data = user.model_dump(exclude_unset=True)

        # Usuários não-privilegiados não podem alterar o próprio tipo
        if not ctx.is_privileged:
            data.pop('tipo', None)

        if data.get('senha'):
            data['senha'] = self.security.get_senha_hash(data['senha'])
        else:
            data.pop('senha', None)

        tipo_antes = user_db.tipo
        for key, value in data.items():
            setattr(user_db, key, value)

        # Mudança de tipo é evento auditável.
        if 'tipo' in data and data['tipo'] != tipo_antes:
            audit_log(
                self.session,
                action='user.tipo_change',
                user_id=ctx.user.id,
                target_type='user',
                target_id=user_db.id,
                payload={'de': tipo_antes, 'para': data['tipo']},
            )

        await self.session.commit()
        await self.session.refresh(user_db)
        return user_db

    async def delete(self, user_id: int, ctx: UserContext):
        """Apenas Admin pode excluir usuários."""

        # sem allowed_tipos → nenhum tipo não-privilegiado passa
        ctx.assert_write()

        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail='Usuário não encontrado.',
            )
        audit_log(
            self.session,
            action='user.delete',
            user_id=ctx.user.id,
            target_type='user',
            target_id=user.id,
            payload={
                'email': user.email,
                'nome': user.nome,
                'tipo': user.tipo,
            },
        )
        await self.session.delete(user)
        await self.session.commit()
        return user
