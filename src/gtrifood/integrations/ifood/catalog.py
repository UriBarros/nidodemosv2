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

    # ===== Criar / Editar =====
    async def create_category(
        self,
        merchant_id: str,
        catalog_id: str,
        name: str,
        external_code: str | None = None,
    ) -> dict[str, Any] | None:
        """Cria nova categoria no catálogo."""
        path = (
            f"/catalog/v2.0/merchants/{merchant_id}"
            f"/catalogs/{catalog_id}/categories"
        )
        body: dict[str, Any] = {"name": name, "status": "AVAILABLE"}
        if external_code:
            body["externalCode"] = external_code
        return await self._client.post(path, json=body)

    async def create_item(
        self,
        merchant_id: str,
        *,
        category_id: str,
        name: str,
        description: str | None = None,
        price: float,
        status: str = "AVAILABLE",
        external_code: str | None = None,
        image_path: str | None = None,
    ) -> dict[str, Any] | None:
        """Cria novo item ligado a uma categoria."""
        path = f"/catalog/v2.0/merchants/{merchant_id}/items"
        body: dict[str, Any] = {
            "name": name,
            "categoryId": category_id,
            "status": status,
            "price": {"value": float(price)},
        }
        if description:
            body["description"] = description
        if external_code:
            body["externalCode"] = external_code
        if image_path:
            body["imagePath"] = image_path
        return await self._client.post(path, json=body)

    async def update_item(
        self,
        merchant_id: str,
        item_id: str,
        *,
        name: str | None = None,
        description: str | None = None,
        image_path: str | None = None,
        external_code: str | None = None,
    ) -> dict[str, Any] | None:
        """Atualiza campos editáveis do item (nome, descrição, foto)."""
        path = f"/catalog/v2.0/merchants/{merchant_id}/items/{item_id}"
        body: dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if image_path is not None:
            body["imagePath"] = image_path
        if external_code is not None:
            body["externalCode"] = external_code
        return await self._client.request("PATCH", path, json=body)

    async def upload_image(
        self,
        merchant_id: str,
        image_bytes: bytes,
        content_type: str = "image/jpeg",
    ) -> dict[str, Any] | None:
        """Faz upload de imagem pra catálogo. Retorna {path: '...'}.

        iFood aceita multipart/form-data com campo 'file'.
        """
        import httpx

        path = f"/catalog/v2.0/merchants/{merchant_id}/image/upload"
        url = f"{self._client._settings.ifood_api_base_url}{path}"
        token = await self._client._get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }
        files = {"file": ("image.jpg", image_bytes, content_type)}
        async with httpx.AsyncClient(timeout=60.0) as cli:
            response = await cli.post(url, headers=headers, files=files)
        if not response.is_success:
            from gtrifood.integrations.ifood.client import IFoodAPIError

            try:
                body = response.json()
            except Exception:
                body = response.text
            raise IFoodAPIError(response.status_code, response.reason_phrase, body)
        return response.json() if response.content else None

    # ===== Option groups (grupos de complementos) =====
    async def list_option_groups(
        self,
        merchant_id: str,
    ) -> list[dict[str, Any]]:
        path = f"/catalog/v2.0/merchants/{merchant_id}/option-groups"
        result = await self._client.get(path)
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            return result.get("optionGroups", [])
        return []

    async def create_option_group(
        self,
        merchant_id: str,
        *,
        name: str,
        min_choices: int = 0,
        max_choices: int = 1,
        external_code: str | None = None,
    ) -> dict[str, Any] | None:
        path = f"/catalog/v2.0/merchants/{merchant_id}/option-groups"
        body: dict[str, Any] = {
            "name": name,
            "min": int(min_choices),
            "max": int(max_choices),
            "status": "AVAILABLE",
        }
        if external_code:
            body["externalCode"] = external_code
        return await self._client.post(path, json=body)

    async def create_option(
        self,
        merchant_id: str,
        *,
        option_group_id: str,
        name: str,
        price: float,
        status: str = "AVAILABLE",
        image_path: str | None = None,
        external_code: str | None = None,
    ) -> dict[str, Any] | None:
        path = f"/catalog/v2.0/merchants/{merchant_id}/options"
        body: dict[str, Any] = {
            "optionGroupId": option_group_id,
            "name": name,
            "price": {"value": float(price)},
            "status": status,
        }
        if image_path:
            body["imagePath"] = image_path
        if external_code:
            body["externalCode"] = external_code
        return await self._client.post(path, json=body)

    async def update_option(
        self,
        merchant_id: str,
        option_id: str,
        *,
        name: str | None = None,
        price: float | None = None,
        status: str | None = None,
        image_path: str | None = None,
    ) -> dict[str, Any] | None:
        path = f"/catalog/v2.0/merchants/{merchant_id}/options/{option_id}"
        body: dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if price is not None:
            body["price"] = {"value": float(price)}
        if status is not None:
            body["status"] = status
        if image_path is not None:
            body["imagePath"] = image_path
        return await self._client.request("PATCH", path, json=body)
