"""
Service do audit log. O `log` é um helper síncrono que adiciona a entry
na sessão — o commit fica por conta do caller (a operação que está
sendo auditada). Assim, se a operação falhar e der rollback, o log
também é descartado (não fica registro de algo que não aconteceu).
"""

from http import HTTPStatus
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.pagination import paginate
from backend.model.audit_log import AuditLog
from backend.security.dependencies import UserContext


def log(  # noqa: PLR0913
    session: AsyncSession,
    *,
    action: str,
    user_id: int | None,
    target_type: str,
    target_id: int | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    """Adiciona uma entry no audit log (commit é do caller)."""
    entry = AuditLog(
        action=action,
        user_id=user_id,
        target_type=target_type,
        target_id=target_id,
        payload=payload,
    )
    session.add(entry)


class AuditLogService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_all(  # noqa: PLR0913
        self,
        ctx: UserContext,
        *,
        action: str | None = None,
        target_type: str | None = None,
        user_id: int | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[AuditLog], int, int]:
        if not ctx.is_privileged:
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail='Apenas Admin pode ler o audit log.',
            )

        query = select(AuditLog)
        if action:
            query = query.where(AuditLog.action == action)
        if target_type:
            query = query.where(AuditLog.target_type == target_type)
        if user_id is not None:
            query = query.where(AuditLog.user_id == user_id)
        query = query.order_by(AuditLog.criado_em.desc())

        items, total, pages = await paginate(
            self.session, query, page, page_size
        )
        return items, total, pages

    async def count(self, ctx: UserContext) -> int:
        if not ctx.is_privileged:
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail='Apenas Admin pode ler o audit log.',
            )
        result = await self.session.execute(
            select(func.count(AuditLog.id))
        )
        return result.scalar_one()
