"""Dependencies do FastAPI — DB session, auth, tenant context."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gtrifood.core.auth import AuthError, AuthUser, decode_supabase_jwt
from gtrifood.core.db import SessionFactory
from gtrifood.models.db import TenantUser


async def get_db() -> AsyncIterator[AsyncSession]:
    """Dependency: sessão DB com commit/rollback automático."""
    async with SessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_current_user(authorization: str = Header(default="")) -> AuthUser:
    """Dependency: extrai e valida o JWT do Supabase do header Authorization."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token Bearer ausente",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization[7:].strip()
    try:
        return decode_supabase_jwt(token)
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def get_current_tenant(
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> uuid.UUID:
    """Dependency: tenant_id do usuário logado (busca em tenant_users)."""
    result = await db.execute(
        select(TenantUser.tenant_id)
        .where(TenantUser.user_id == user.user_id)
        .limit(1)
    )
    tenant_id = result.scalar_one_or_none()
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário sem tenant vinculado",
        )
    return tenant_id
