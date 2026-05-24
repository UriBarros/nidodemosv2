"""Endpoints do módulo Review da API iFood."""

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
        """Lista avaliações paginadas.

        Resposta tem `reviews: [...]`, `total`, `page`, `pageSize`.
        """
        params = {
            "page": page,
            "pageSize": page_size,
            "sort": sort,
            "sortDirection": sort_direction,
        }
        return await self._client.get(
            f"/review/v1.0/merchants/{merchant_id}/reviews",
            params=params,
        )

    async def answer(
        self,
        merchant_id: str,
        review_id: str,
        text: str,
    ) -> None:
        """Responde uma avaliação."""
        await self._client.post(
            f"/review/v1.0/merchants/{merchant_id}/reviews/{review_id}/answers",
            json={"text": text},
        )
