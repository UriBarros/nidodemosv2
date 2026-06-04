"""iFood Catalog API v2.0 — cardápios, categorias e itens.

Endpoints principais:
- GET    /catalog/v2.0/merchants/{merchantId}/catalogs
- GET    /catalog/v2.0/merchants/{merchantId}/catalogs/{catalogId}/categories
- GET    /catalog/v2.0/merchants/{merchantId}/items
- PATCH  /catalog/v2.0/merchants/{merchantId}/items/status
- PATCH  /catalog/v2.0/merchants/{merchantId}/items/price

Referência: https://developer.ifood.com.br/pt-BR/docs/references/catalog/
"""

from __future__ import annotations

from typing import Any

from gtrifood.integrations.ifood.client import IFoodClient


class CatalogAPI:
    """Wrapper da Catalog API do iFood."""

    def __init__(self, client: IFoodClient) -> None:
        self._client = client

    # ===== Catálogos =====
    async def list_catalogs(self, merchant_id: str) -> list[dict[str, Any]]:
        """Lista catálogos do merchant. Geralmente retorna 1."""
        path = f"/catalog/v2.0/merchants/{merchant_id}/catalogs"
        result = await self._client.get(path)
        if isinstance(result, list):
            return result
        return result.get("catalogs", []) if isinstance(result, dict) else []

    # ===== Categorias =====
    async def list_categories(
        self,
        merchant_id: str,
        catalog_id: str,
        include_items: bool = True,
    ) -> list[dict[str, Any]]:
        """Lista categorias de um catálogo. include_items embute itens."""
        path = (
            f"/catalog/v2.0/merchants/{merchant_id}"
            f"/catalogs/{catalog_id}/categories"
        )
        params = {"includeItems": "true"} if include_items else None
        result = await self._client.get(path, params=params)
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            return result.get("categories", [])
        return []

    # ===== Itens =====
    async def list_items(self, merchant_id: str) -> list[dict[str, Any]]:
        """Lista todos os itens do merchant (flatten)."""
        path = f"/catalog/v2.0/merchants/{merchant_id}/items"
        result = await self._client.get(path)
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            return result.get("items", [])
        return []

    async def update_item_status(
        self,
        merchant_id: str,
        item_id: str,
        status: str,  # AVAILABLE | UNAVAILABLE
    ) -> dict[str, Any] | None:
        """Atualiza disponibilidade de um item."""
        path = f"/catalog/v2.0/merchants/{merchant_id}/items/status"
        body = {"itemId": item_id, "status": status}
        return await self._client.request("PATCH", path, json=body)

    async def update_item_price(
        self,
        merchant_id: str,
        item_id: str,
        price: float,
    ) -> dict[str, Any] | None:
        """Atualiza preço de um item."""
        path = f"/catalog/v2.0/merchants/{merchant_id}/items/price"
        body = {"itemId": item_id, "price": {"value": float(price)}}
        return await self._client.request("PATCH", path, json=body)
