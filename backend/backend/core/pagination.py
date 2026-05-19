"""Helper genérico de paginação para queries do SQLAlchemy async."""
from math import ceil
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession


async def paginate(
    session: AsyncSession,
    query: Select[Any],
    page: int,
    page_size: int,
) -> tuple[list[Any], int, int]:
    """
    Executa `query` paginada e retorna (items, total, pages).
    `query` deve ser um Select já com filtros aplicados; este helper
    adiciona apenas offset/limit e calcula o total.
    """
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar() or 0

    items_query = query.offset((page - 1) * page_size).limit(page_size)
    items = (await session.execute(items_query)).scalars().all()

    pages = max(1, ceil(total / page_size)) if total > 0 else 1
    return list(items), total, pages
