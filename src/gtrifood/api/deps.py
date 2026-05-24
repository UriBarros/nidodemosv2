"""Dependencies do FastAPI — DB session, tenant context, auth (futuro)."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

from fastapi import Header
from sqlalchemy.ext.asyncio import AsyncSession

from gtrifood.core.db import SessionFactory

# Tenant default no MVP — futuramente vem do JWT do Supabase Auth
DEFAULT_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def get_db() -> AsyncIterator[AsyncSession]:
    """Dependency: sessão DB com commit/rollback automático."""
    async with SessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_tenant_id(x_tenant_id: str | None = Header(default=None)) -> uuid.UUID:
    """Dependency: tenant_id do request. No MVP usa default; depois vem do JWT."""
    if x_tenant_id:
        try:
            return uuid.UUID(x_tenant_id)
        except ValueError:
            pass
    return DEFAULT_TENANT_ID
