"""iFood Catalog API v2.0 — workflow atualizado conforme docs oficiais.

Refs:
- https://developer.ifood.com.br/pt-BR/docs/guides/modules/catalog/workflow
- https://developer.ifood.com.br/pt-BR/docs/guides/modules/catalog/fundamentals

Mudanças importantes vs versão anterior:
- Categoria: POST direto em /categories (sem /catalogs/{id}/categories)
- Item: PUT idempotente em /items com estrutura aninhada
  {item, products, optionGroups, options}
- IDs do item/produto/option: UUID v4 gerados client-side
- Complementos: NÃO há endpoints /option-groups e /options separados.
  Tudo vai dentro do PUT /items (cada chamada substitui item inteiro).
- externalCode: identificador opcional para integração com POS.

Atualização de preço/status: tem endpoints PATCH dedicados
(/items/status e /items/price) que aceitam itemId. Mantidos pra UX rápida.
"""

from __future__ import annotations

import uuid
from typing import Any

import httpx

from gtrifood.integrations.ifood.client import IFoodAPIError, IFoodClient


def new_uuid() -> str:
    """Gera UUID v4 string (formato 8-4-4-4-12)."""
    return str(uuid.uuid4())


class CatalogAPI:
    """Wrapper da Catalog API v2.0 do iFood."""

    def __init__(self, client: IFoodClient) -> None:
        self._client = client

    # ===== Catálogos =====
    async def list_catalogs(self, merchant_id: str) -> list[dict[str, Any]]:
        """GET /catalog/v2.0/merchants/{id}/catalogs — lista catálogos."""
        result = await self._client.get(
            f"/catalog/v2.0/merchants/{merchant_id}/catalogs"
        )
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            return result.get("catalogs", [])
        return []

    # ===== Categorias =====
    async def list_categories(
        self, merchant_id: str, *, include_items: bool = False
    ) -> list[dict[str, Any]]:
        """GET /catalog/v2.0/merchants/{id}/categories — lista categorias."""
        params = {"includeItems": "true"} if include_items else None
        result = await self._client.get(
            f"/catalog/v2.0/merchants/{merchant_id}/categories",
            params=params,
        )
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            return result.get("categories", [])
        return []

    async def create_category(
        self,
        merchant_id: str,
        *,
        name: str,
        template: str = "DEFAULT",  # DEFAULT | PIZZA
        status: str = "AVAILABLE",
        external_code: str | None = None,
    ) -> dict[str, Any] | None:
        """POST /catalog/v2.0/merchants/{id}/categories — cria categoria."""
        body: dict[str, Any] = {
            "name": name,
            "status": status,
            "template": template,
        }
        if external_code:
            body["externalCode"] = external_code
        return await self._client.post(
            f"/catalog/v2.0/merchants/{merchant_id}/categories",
            json=body,
        )

    async def list_items_in_category(
        self, merchant_id: str, category_id: str
    ) -> list[dict[str, Any]]:
        """GET /catalog/v2.0/merchants/{id}/categories/{categoryId}/items."""
        result = await self._client.get(
            f"/catalog/v2.0/merchants/{merchant_id}"
            f"/categories/{category_id}/items"
        )
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            return result.get("items", [])
        return []

    # ===== Itens (PUT idempotente — estrutura aninhada) =====
    async def put_item(
        self,
        merchant_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any] | None:
        """PUT /catalog/v2.0/merchants/{id}/items — cria ou substitui item completo.

        payload deve ter a estrutura:
            {
              "item": {id, type, categoryId, status, price, externalCode, ...},
              "products": [...],
              "optionGroups": [...],
              "options": [...]
            }

        Todos os 4 campos são obrigatórios mesmo que vazios.
        Cada chamada substitui o item por completo (idempotente).
        """
        path = f"/catalog/v2.0/merchants/{merchant_id}/items"
        return await self._client.request("PUT", path, json=payload)

    @staticmethod
    def build_simple_item(
        *,
        category_id: str,
        name: str,
        price: float,
        description: str | None = None,
        status: str = "AVAILABLE",
        external_code: str | None = None,
        image_path: str | None = None,
        item_id: str | None = None,
        product_id: str | None = None,
    ) -> dict[str, Any]:
        """Constrói payload mínimo de item simples (sem complementos)."""
        iid = item_id or new_uuid()
        pid = product_id or new_uuid()
        product: dict[str, Any] = {"id": pid, "name": name}
        if description:
            product["description"] = description
        if external_code:
            product["externalCode"] = f"{external_code}_PROD"
        item: dict[str, Any] = {
            "id": iid,
            "type": "DEFAULT",
            "categoryId": category_id,
            "status": status,
            "price": {"value": float(price)},
        }
        if external_code:
            item["externalCode"] = external_code
        if image_path:
            item["imagePath"] = image_path
        return {
            "item": item,
            "products": [product],
            "optionGroups": [],
            "options": [],
        }

    @staticmethod
    def build_item_with_options(
        *,
        base: dict[str, Any],
        option_groups: list[dict[str, Any]],
        options: list[dict[str, Any]],
        products_extras: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Adiciona grupos + opções ao payload base (mantém idempotência)."""
        out = {
            "item": base["item"],
            "products": list(base.get("products", [])),
            "optionGroups": list(option_groups),
            "options": list(options),
        }
        if products_extras:
            out["products"].extend(products_extras)
        return out

    # ===== Atualizações pontuais (preço/status) =====
    async def update_item_status(
        self,
        merchant_id: str,
        item_id: str,
        status: str,
    ) -> dict[str, Any] | None:
        """PATCH /catalog/v2.0/merchants/{id}/items/status — pausar/ativar item."""
        body = {"itemId": item_id, "status": status}
        return await self._client.request(
            "PATCH",
            f"/catalog/v2.0/merchants/{merchant_id}/items/status",
            json=body,
        )

    async def update_item_price(
        self,
        merchant_id: str,
        item_id: str,
        price: float,
    ) -> dict[str, Any] | None:
        """PATCH /catalog/v2.0/merchants/{id}/items/price — atualiza preço."""
        body = {"itemId": item_id, "price": {"value": float(price)}}
        return await self._client.request(
            "PATCH",
            f"/catalog/v2.0/merchants/{merchant_id}/items/price",
            json=body,
        )

    async def update_option_status(
        self,
        merchant_id: str,
        option_id: str,
        status: str,
    ) -> dict[str, Any] | None:
        """PATCH /catalog/v2.0/merchants/{id}/options/status — pausar/ativar opção."""
        body = {"optionId": option_id, "status": status}
        return await self._client.request(
            "PATCH",
            f"/catalog/v2.0/merchants/{merchant_id}/options/status",
            json=body,
        )

    async def update_option_price(
        self,
        merchant_id: str,
        option_id: str,
        price: float,
    ) -> dict[str, Any] | None:
        """PATCH /catalog/v2.0/merchants/{id}/options/price — atualiza preço opção."""
        body = {"optionId": option_id, "price": {"value": float(price)}}
        return await self._client.request(
            "PATCH",
            f"/catalog/v2.0/merchants/{merchant_id}/options/price",
            json=body,
        )

    # ===== Upload de imagem =====
    async def upload_image(
        self,
        merchant_id: str,
        image_bytes: bytes,
        content_type: str = "image/jpeg",
    ) -> dict[str, Any] | None:
        """POST /catalog/v2.0/merchants/{id}/image/upload — multipart.

        Retorna {path: "..."} usado em item.imagePath.
        """
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
            try:
                body = response.json()
            except Exception:
                body = response.text
            raise IFoodAPIError(
                response.status_code, response.reason_phrase, body
            )
        return response.json() if response.content else None
