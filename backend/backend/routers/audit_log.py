from http import HTTPStatus
from typing import Annotated

from fastapi import Depends, Query
from fastapi.routing import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.engine import EngineApp
from backend.schemas.audit_log import AuditLogList
from backend.security.dependencies import Dependencies, UserContext
from backend.service.audit_log import AuditLogService

router_audit_log = APIRouter(prefix='/audit-log', tags=['audit-log'])

T_AsyncSession = Annotated[AsyncSession, Depends(EngineApp.get_async_session)]
T_UserContext = Annotated[UserContext, Depends(Dependencies.get_user_context)]


@router_audit_log.get(
    '/', status_code=HTTPStatus.OK, response_model=AuditLogList
)
async def get(  # noqa: PLR0913, PLR0917
    session: T_AsyncSession,
    ctx: T_UserContext,
    action: str | None = Query(None, description='Filtra por action'),
    target_type: str | None = Query(
        None, description='Filtra por target_type'
    ),
    user_id: int | None = Query(None, description='Filtra por autor'),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
):
    service = AuditLogService(session)
    items, total, pages = await service.list_all(
        ctx,
        action=action,
        target_type=target_type,
        user_id=user_id,
        page=page,
        page_size=page_size,
    )
    return {
        'items': items,
        'total': total,
        'page': page,
        'page_size': page_size,
        'pages': pages,
    }
