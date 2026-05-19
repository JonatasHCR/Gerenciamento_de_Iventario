from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditLogRead(BaseModel):
    id: int
    action: str
    user_id: int | None = None
    target_type: str
    target_id: int | None = None
    payload: dict[str, Any] | None = None
    criado_em: datetime

    model_config = {'from_attributes': True}


class AuditLogList(BaseModel):
    items: list[AuditLogRead]
    total: int
    page: int
    page_size: int
    pages: int
