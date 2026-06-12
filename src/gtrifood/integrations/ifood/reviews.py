"""Endpoints do módulo Review da API iFood — v2.0.

Mudança v1.0 → v2.0:
- Path passa de /review/v1.0/... pra /review/v2.0/...
- Novos endpoints: GET /reviews/{id} (detalhes) e GET /summary (agregado)
"""

from __future__ import annotations

from typing import Any

from gtrifood.integrations.ifood.client import IFoodClient


class ReviewsAPI:
    def __init__(self, client: IFoodClient) -> None:
        self._client = client

    async def list_reviews(
        self,
        merchant_id: str,
        *,
        page: int = 1,
        page_size: int = 50,
        sort: str = "CREATED_AT",
        sort_direction: str = "DESC",
    ) -> dict[str, Any]:
        """GET /review/v2.0/merchants/{id}/reviews — lista paginada."""
        params = {
            "page": page,
            "pageSize": page_size,
            "sort": sort,
            "sortDirection": sort_direction,
        }
        return await self._client.get(
            f"/review/v2.0/merchants/{merchant_id}/reviews",
            params=params,
        )

    async def get_review(
        self,
        merchant_id: str,
        review_id: str,
    ) -> dict[str, Any]:
        """GET /review/v2.0/merchants/{id}/reviews/{reviewId} — detalhes."""
        return await self._client.get(
            f"/review/v2.0/merchants/{merchant_id}/reviews/{review_id}"
        )

    async def get_summary(self, merchant_id: str) -> dict[str, Any]:
        """GET /review/v2.0/merchants/{id}/summary — agregado (count, avg score)."""
        return await self._client.get(
            f"/review/v2.0/merchants/{merchant_id}/summary"
        )

    async def answer(
        self,
        merchant_id: str,
        review_id: str,
        text: str,
    ) -> None:
        """POST /review/v2.0/merchants/{id}/reviews/{reviewId}/answers."""
        await self._client.post(
            f"/review/v2.0/merchants/{merchant_id}/reviews/{review_id}/answers",
            json={"text": text},
        )
