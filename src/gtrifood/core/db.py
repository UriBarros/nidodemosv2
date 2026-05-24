"""Conexão Postgres (Supabase) via SQLAlchemy async.

Uso:
    async with get_session() as session:
        result = await session.execute(select(Merchant))
        merchants = result.scalars().all()
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from gtrifood.config import get_settings


def _build_async_url(db_url: str) -> str:
    """Converte `postgresql://...` → `postgresql+psycopg://...` (driver async psycopg3)."""
    if db_url.startswith("postgresql+psycopg"):
        return db_url
    if db_url.startswith("postgresql://"):
        return db_url.replace("postgresql://", "postgresql+psycopg://", 1)
    if db_url.startswith("postgres://"):
        return db_url.replace("postgres://", "postgresql+psycopg://", 1)
    return db_url


_settings = get_settings()
_async_url = _build_async_url(_settings.database_url.get_secret_value())

engine = create_async_engine(
    _async_url,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    # Supabase Pooler (PgBouncer transaction mode) não suporta prepared statements
    # persistentes — desliga via psycopg3.
    connect_args={"prepare_threshold": None},
)

SessionFactory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    """Context manager para sessão async com commit/rollback automático."""
    async with SessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
