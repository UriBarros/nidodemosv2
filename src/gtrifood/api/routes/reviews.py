"""Endpoints de reviews."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from gtrifood.api.deps import get_current_tenant, get_db
from gtrifood.api.schemas import ReviewOut, SyncResultOut
from gtrifood.models.db import Review
from gtrifood.services.reviews_sync import sync_reviews_for_merchant

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.get("", response_model=list[ReviewOut])
async def list_reviews(
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    merchant_id: uuid.UUID | None = Query(default=None),
    min_score: int | None = Query(default=None, ge=1, le=5),
    answered: bool | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[Review]:
    stmt = select(Review).where(Review.tenant_id == tenant_id)
    if merchant_id:
        stmt = stmt.where(Review.merchant_id == merchant_id)
    if min_score is not None:
        stmt = stmt.where(Review.score >= min_score)
    if answered is not None:
        stmt = stmt.where(Review.answered == answered)
    stmt = stmt.order_by(desc(Review.created_at_ifood)).limit(limit)

    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/summary")
async def reviews_summary(
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    merchant_id: uuid.UUID | None = Query(default=None),
) -> dict[str, float | int]:
    """Métricas agregadas: total, média de score, % respondidas."""
    stmt = select(
        func.count(Review.id),
        func.avg(Review.score),
        func.sum(case((Review.answered.is_(True), 1), else_=0)),
    ).where(Review.tenant_id == tenant_id)
    if merchant_id:
        stmt = stmt.where(Review.merchant_id == merchant_id)

    result = (await db.execute(stmt)).one()
    total = int(result[0] or 0)
    avg = float(result[1]) if result[1] is not None else 0.0
    answered_count = int(result[2] or 0)
    pct_answered = (answered_count / total * 100) if total else 0.0

    return {
        "total": total,
        "average_score": round(avg, 2),
        "answered_count": answered_count,
        "answered_pct": round(pct_answered, 1),
    }


@router.post("/sync", response_model=SyncResultOut)
async def trigger_reviews_sync(
    merchant_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
) -> SyncResultOut:
    try:
        count = await sync_reviews_for_merchant(tenant_id, merchant_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return SyncResultOut(inserted=count, message=f"{count} review(s) sincronizado(s)")
