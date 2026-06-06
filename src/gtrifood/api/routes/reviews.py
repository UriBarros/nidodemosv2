"""Endpoints de reviews."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from gtrifood.api.deps import get_current_tenant, get_db
from gtrifood.api.schemas import ReviewOut, ReviewReplyIn, SyncResultOut
from gtrifood.integrations.ifood.client import IFoodAPIError, IFoodClient
from gtrifood.integrations.ifood.reviews import ReviewsAPI
from gtrifood.models.db import Merchant, Review
from gtrifood.services.reviews_sync import sync_reviews_for_merchant

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.get("", response_model=list[ReviewOut])
async def list_reviews(
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    client_id: uuid.UUID | None = Query(default=None),
    merchant_id: uuid.UUID | None = Query(default=None),
    min_score: int | None = Query(default=None, ge=1, le=5),
    answered: bool | None = Query(default=None),
    begin: str | None = Query(default=None, description="ISO datetime — created_at_ifood >= begin"),
    end: str | None = Query(default=None, description="ISO datetime — created_at_ifood <= end"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[Review]:
    stmt = select(Review).where(Review.tenant_id == tenant_id)
    if client_id:
        stmt = stmt.join(Merchant, Review.merchant_id == Merchant.id).where(
            Merchant.client_id == client_id
        )
    if merchant_id:
        stmt = stmt.where(Review.merchant_id == merchant_id)
    if min_score is not None:
        stmt = stmt.where(Review.score >= min_score)
    if answered is not None:
        stmt = stmt.where(Review.answered == answered)
    if begin:
        stmt = stmt.where(Review.created_at_ifood >= begin)
    if end:
        stmt = stmt.where(Review.created_at_ifood <= end)
    stmt = stmt.order_by(desc(Review.created_at_ifood)).limit(limit).offset(offset)

    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{review_id}", response_model=ReviewOut)
async def get_review(
    review_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
) -> Review:
    result = await db.execute(
        select(Review).where(
            Review.id == review_id, Review.tenant_id == tenant_id
        )
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="avaliação não encontrada")
    return review


@router.post("/{review_id}/reply", response_model=ReviewOut)
async def reply_to_review(
    review_id: uuid.UUID,
    payload: ReviewReplyIn,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
) -> Review:
    """Responde uma avaliação. Propaga pro iFood e marca como respondida local."""
    text = (payload.text or "").strip()
    if not text:
        raise HTTPException(400, "texto da resposta não pode ser vazio")
    if len(text) > 1000:
        raise HTTPException(400, "texto da resposta excede 1000 caracteres")

    result = await db.execute(
        select(Review).where(
            Review.id == review_id, Review.tenant_id == tenant_id
        )
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(404, "avaliação não encontrada")

    if review.answered:
        raise HTTPException(409, "avaliação já respondida — iFood não permite reenviar")

    # Pega merchant + token correto (per-client ou client_credentials)
    m_result = await db.execute(
        select(Merchant.ifood_merchant_id, Merchant.client_id).where(
            Merchant.id == review.merchant_id
        )
    )
    m_row = m_result.first()
    if not m_row:
        raise HTTPException(404, "merchant da avaliação não encontrado")
    ifood_merchant_id, client_id = m_row

    if client_id:
        from gtrifood.services.client_tokens import get_or_refresh_access_token

        async def _tp() -> str:
            return await get_or_refresh_access_token(client_id)

        ifood_client = IFoodClient(token_provider=_tp)
    else:
        ifood_client = IFoodClient()

    api = ReviewsAPI(ifood_client)
    try:
        await api.answer(ifood_merchant_id, review.ifood_review_id, text)
    except IFoodAPIError as e:
        # iFood pode rejeitar: review já respondida, status incorreto, etc
        raise HTTPException(
            status_code=400 if 400 <= e.status_code < 500 else 502,
            detail=f"iFood rejeitou resposta: {e.body}",
        ) from e

    review.answered = True
    review.answer_text = text
    review.answered_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(review)
    return review


@router.get("/summary")
async def reviews_summary(
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    client_id: uuid.UUID | None = Query(default=None),
    merchant_id: uuid.UUID | None = Query(default=None),
    begin: str | None = Query(default=None),
    end: str | None = Query(default=None),
) -> dict[str, float | int]:
    """Métricas agregadas: total, média de score, % respondidas."""
    stmt = select(
        func.count(Review.id),
        func.avg(Review.score),
        func.sum(case((Review.answered.is_(True), 1), else_=0)),
    ).where(Review.tenant_id == tenant_id)
    if client_id:
        stmt = stmt.join(Merchant, Review.merchant_id == Merchant.id).where(
            Merchant.client_id == client_id
        )
    if merchant_id:
        stmt = stmt.where(Review.merchant_id == merchant_id)
    if begin:
        stmt = stmt.where(Review.created_at_ifood >= begin)
    if end:
        stmt = stmt.where(Review.created_at_ifood <= end)

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
