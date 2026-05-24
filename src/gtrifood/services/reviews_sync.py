"""Sync de reviews — pagina todas as avaliações do merchant e UPSERT."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from gtrifood.core.db import get_session
from gtrifood.core.logging import get_logger
from gtrifood.integrations.ifood.client import IFoodAPIError, IFoodClient
from gtrifood.integrations.ifood.reviews import ReviewsAPI
from gtrifood.models.db import Merchant, Review

logger = get_logger(__name__)


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


async def sync_reviews_for_merchant(
    tenant_id: uuid.UUID,
    merchant_id: uuid.UUID,
    *,
    max_pages: int = 20,
    page_size: int = 50,
) -> int:
    """Pagina reviews do iFood e UPSERT. Retorna total processado."""
    async with get_session() as session:
        merchant = (
            await session.execute(select(Merchant).where(Merchant.id == merchant_id))
        ).scalar_one_or_none()
        if not merchant:
            raise ValueError(f"Merchant {merchant_id} não encontrado")
        ifood_id = merchant.ifood_merchant_id

    api = ReviewsAPI(IFoodClient())
    total_processed = 0

    for page in range(1, max_pages + 1):
        try:
            response = await api.list_reviews(ifood_id, page=page, page_size=page_size)
        except IFoodAPIError as e:
            if 400 <= e.status_code < 500:
                logger.warning(
                    "reviews_endpoint_indisponivel",
                    status=e.status_code,
                    merchant_id=str(merchant_id),
                )
                break
            raise
        reviews_page = response.get("reviews") or []
        if not reviews_page:
            break

        async with get_session() as session:
            for r in reviews_page:
                stmt = insert(Review).values(
                    tenant_id=tenant_id,
                    merchant_id=merchant_id,
                    ifood_review_id=r["id"],
                    ifood_order_id=r.get("order", {}).get("id") if isinstance(r.get("order"), dict) else r.get("orderId"),
                    score=r.get("score"),
                    comment=r.get("comment"),
                    customer_name=(r.get("customer") or {}).get("name"),
                    answered=bool(r.get("moderated") or r.get("answered")),
                    answer_text=(r.get("answer") or {}).get("text") if isinstance(r.get("answer"), dict) else None,
                    answered_at=_parse_dt((r.get("answer") or {}).get("createdAt") if isinstance(r.get("answer"), dict) else None),
                    created_at_ifood=_parse_dt(r.get("createdAt")),
                    raw_data=r,
                )
                stmt = stmt.on_conflict_do_update(
                    index_elements=["tenant_id", "ifood_review_id"],
                    set_={
                        "score": stmt.excluded.score,
                        "comment": stmt.excluded.comment,
                        "answered": stmt.excluded.answered,
                        "answer_text": stmt.excluded.answer_text,
                        "answered_at": stmt.excluded.answered_at,
                        "raw_data": stmt.excluded.raw_data,
                    },
                )
                await session.execute(stmt)

        total_processed += len(reviews_page)
        if len(reviews_page) < page_size:
            break

    logger.info("reviews_sincronizados", merchant_id=str(merchant_id), total=total_processed)
    return total_processed
