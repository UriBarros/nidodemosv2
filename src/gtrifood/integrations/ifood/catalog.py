"""iFood Catalog API v2.0 — adaptado ao Swagger oficial de jun/2026.

Server base: https://merchant-api.ifood.com.br/catalog/v2.0/

Mudanças relevantes vs implementação antiga:
- PUT /items é o endpoint canônico de create/update (idempotente, body
  completo com optionGroups + options aninhados). Não existe POST /items.
- PATCH /items/{itemId} (JSON Merge Patch) substitui /items/status e
  /items/price, ambos deprecated.
- Option groups usam camelCase: /optionGroups (não /option-groups).
- Não existe POST /optionGroups standalone — grupo nasce do PUT /items.
- Não existe POST /options standalone — usa /optionGroups/{ogId}/options.
- Não existe PATCH /options/{id} individual — pausar/precificar via batch
  endpoints /options/status, /options/price, /options/externalCode.
- Produto (Product) é entidade base separada de Item; muitos endpoints
  novos: /products CRUD + /products/{id}, /products/status, /products/price.

Referência: https://developer.ifood.com.br/docs/references#catalog
"""

from __future__ import annotations

from typing import Any

from gtrifood.integrations.ifood.client import IFoodClient


class CatalogAPI:
    """Wrapper da Catalog API v2.0 do iFood."""

    BASE = "/catalog/v2.0"

    def __init__(self, client: IFoodClient) -> None:
        self._client = client

    def _p(self, path: str) -> str:
        return f"{self.BASE}{path}"

    # =========================================================================
    # Catalog
    # =========================================================================
    async def list_catalogs(self, merchant_id: str) -> list[dict[str, Any]]:
        """Lista catálogos do merchant. Geralmente retorna 1."""
        result = await self._client.get(self._p(f"/merchants/{merchant_id}/catalogs"))
        if isinstance(result, list):
            return result
        return result.get("catalogs", []) if isinstance(result, dict) else []

    async def list_unsellable_items(
        self, merchant_id: str, catalog_id: str
    ) -> list[dict[str, Any]]:
        """Itens fora do ar (sem foto, sem categoria etc)."""
        path = self._p(
            f"/merchants/{merchant_id}/catalogs/{catalog_id}/unsellableItems"
        )
        result = await self._client.get(path)
        if isinstance(result, list):
            return result
        return result.get("items", []) if isinstance(result, dict) else []

    async def list_sellable_items(
        self, merchant_id: str, group_id: str
    ) -> list[dict[str, Any]]:
        """Itens vendáveis (no ar). group_id geralmente == catalog_id."""
        path = self._p(
            f"/merchants/{merchant_id}/catalogs/{group_id}/sellableItems"
        )
        result = await self._client.get(path)
        if isinstance(result, list):
            return result
        return result.get("items", []) if isinstance(result, dict) else []

    async def check_version(self, merchant_id: str) -> dict[str, Any]:
        """Retorna versão atual do catálogo (v1 ou v2)."""
        result = await self._client.get(
            self._p(f"/merchants/{merchant_id}/catalog/version")
        )
        return result if isinstance(result, dict) else {"version": result}

    # =========================================================================
    # Category
    # =========================================================================
    async def list_categories(
        self,
        merchant_id: str,
        catalog_id: str,
        include_items: bool = True,
    ) -> list[dict[str, Any]]:
        """Lista categorias de um catálogo. include_items embute itens."""
        path = self._p(
            f"/merchants/{merchant_id}/catalogs/{catalog_id}/categories"
        )
        params = {"includeItems": "true"} if include_items else None
        result = await self._client.get(path, params=params)
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            return result.get("categories", [])
        return []

    async def get_category(
        self, merchant_id: str, catalog_id: str, category_id: str
    ) -> dict[str, Any]:
        """Detalhes de uma categoria."""
        path = self._p(
            f"/merchants/{merchant_id}/catalogs/{catalog_id}"
            f"/categories/{category_id}"
        )
        return await self._client.get(path)

    async def create_category(
        self,
        merchant_id: str,
        catalog_id: str,
        name: str,
        external_code: str | None = None,
        template: str = "DEFAULT",
    ) -> dict[str, Any] | None:
        """Cria nova categoria no catálogo."""
        path = self._p(
            f"/merchants/{merchant_id}/catalogs/{catalog_id}/categories"
        )
        body: dict[str, Any] = {
            "name": name,
            "status": "AVAILABLE",
            "template": template,
        }
        if external_code:
            body["externalCode"] = external_code
        return await self._client.post(path, json=body)

    async def edit_category(
        self,
        merchant_id: str,
        catalog_id: str,
        category_id: str,
        *,
        name: str | None = None,
        status: str | None = None,
        external_code: str | None = None,
    ) -> dict[str, Any] | None:
        """Edita categoria (PATCH parcial)."""
        path = self._p(
            f"/merchants/{merchant_id}/catalogs/{catalog_id}"
            f"/categories/{category_id}"
        )
        body: dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if status is not None:
            body["status"] = status
        if external_code is not None:
            body["externalCode"] = external_code
        return await self._client.request("PATCH", path, json=body)

    async def delete_category(self, merchant_id: str, category_id: str) -> None:
        """Remove categoria. Note: path SEM catalogId."""
        await self._client.request(
            "DELETE",
            self._p(f"/merchants/{merchant_id}/categories/{category_id}"),
        )

    async def list_category_items(
        self, merchant_id: str, category_id: str
    ) -> list[dict[str, Any]]:
        """Itens de uma categoria. Path SEM catalogId."""
        path = self._p(
            f"/merchants/{merchant_id}/categories/{category_id}/items"
        )
        result = await self._client.get(path)
        if isinstance(result, list):
            return result
        return result.get("items", []) if isinstance(result, dict) else []

    # =========================================================================
    # Product (entidade base; item conecta produto a categoria)
    # =========================================================================
    async def list_products(self, merchant_id: str) -> list[dict[str, Any]]:
        """Lista todos os produtos do merchant."""
        result = await self._client.get(
            self._p(f"/merchants/{merchant_id}/products")
        )
        if isinstance(result, list):
            return result
        return result.get("products", []) if isinstance(result, dict) else []

    async def get_product(
        self, merchant_id: str, product_id: str
    ) -> dict[str, Any]:
        """Detalhes de um produto."""
        return await self._client.get(
            self._p(f"/merchants/{merchant_id}/product/{product_id}")
        )

    async def get_product_by_external_code(
        self, merchant_id: str, external_code: str
    ) -> list[dict[str, Any]]:
        """Busca produtos por externalCode."""
        path = self._p(
            f"/merchants/{merchant_id}/products/externalCode/{external_code}"
        )
        result = await self._client.get(path)
        if isinstance(result, list):
            return result
        return result.get("products", []) if isinstance(result, dict) else []

    async def create_product(
        self,
        merchant_id: str,
        *,
        name: str,
        description: str | None = None,
        image_path: str | None = None,
        external_code: str | None = None,
        ean: str | None = None,
    ) -> dict[str, Any] | None:
        """Cria produto novo (entidade base, sem categoria/preço ainda)."""
        body: dict[str, Any] = {"name": name}
        if description:
            body["description"] = description
        if image_path:
            body["imagePath"] = image_path
        if external_code:
            body["externalCode"] = external_code
        if ean:
            body["ean"] = ean
        return await self._client.post(
            self._p(f"/merchants/{merchant_id}/products"), json=body
        )

    async def update_product(
        self,
        merchant_id: str,
        product_id: str,
        *,
        name: str,
        description: str | None = None,
        image_path: str | None = None,
        external_code: str | None = None,
    ) -> dict[str, Any] | None:
        """Substitui produto inteiro (PUT idempotente)."""
        body: dict[str, Any] = {"name": name}
        if description is not None:
            body["description"] = description
        if image_path is not None:
            body["imagePath"] = image_path
        if external_code is not None:
            body["externalCode"] = external_code
        return await self._client.request(
            "PUT",
            self._p(f"/merchants/{merchant_id}/products/{product_id}"),
            json=body,
        )

    async def patch_product(
        self,
        merchant_id: str,
        product_id: str,
        *,
        name: str | None = None,
        description: str | None = None,
        image_path: str | None = None,
        external_code: str | None = None,
    ) -> dict[str, Any] | None:
        """Patch parcial (JSON Merge Patch) — só envia campos não-None."""
        body: dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if image_path is not None:
            body["imagePath"] = image_path
        if external_code is not None:
            body["externalCode"] = external_code
        return await self._client.request(
            "PATCH",
            self._p(f"/merchants/{merchant_id}/products/{product_id}"),
            json=body,
        )

    async def delete_product(self, merchant_id: str, product_id: str) -> None:
        await self._client.request(
            "DELETE",
            self._p(f"/merchants/{merchant_id}/products/{product_id}"),
        )

    async def batch_update_products_status(
        self, merchant_id: str, updates: list[dict[str, str]]
    ) -> dict[str, Any] | None:
        """Atualiza status de N produtos. updates = [{productId, status}, ...]."""
        return await self._client.request(
            "PATCH",
            self._p(f"/merchants/{merchant_id}/products/status"),
            json=updates,
        )

    async def batch_update_products_price(
        self,
        merchant_id: str,
        updates: list[dict[str, Any]],
        resources: str = "BOTH",
    ) -> dict[str, Any] | None:
        """Atualiza preço de N produtos. resources: ITEM|OPTION|BOTH.

        updates = [{productId, price:{value: X}, originalPrice:{value: Y}}, ...]
        """
        return await self._client.request(
            "PATCH",
            self._p(f"/merchants/{merchant_id}/products/price"),
            params={"resources": resources},
            json=updates,
        )

    # =========================================================================
    # Item (slot de Product na Category com price/status/optionGroups)
    # =========================================================================
    async def get_item_flat(
        self, merchant_id: str, item_id: str
    ) -> dict[str, Any]:
        """Detalhes flat do item (product + price + optionGroups)."""
        return await self._client.get(
            self._p(f"/merchants/{merchant_id}/items/{item_id}/flat")
        )

    async def upsert_item(
        self,
        merchant_id: str,
        *,
        category_id: str,
        item: dict[str, Any],
    ) -> dict[str, Any] | None:
        """PUT /items — cria ou atualiza item completo (idempotente).

        `item` deve seguir shape do iFood:
        {
          "id": "<existing item id>",     # opcional p/ novo
          "categoryId": "<cat>",
          "product": {                    # produto inline
            "id": "<existing>",           # opcional p/ novo
            "name": "...",
            "description": "...",
            "imagePath": "..."
          },
          "price": {"value": 12.5},
          "status": "AVAILABLE",
          "externalCode": "...",
          "optionGroups": [
            {
              "id": "<existing>", "name": "...", "min": 0, "max": 1,
              "status": "AVAILABLE",
              "options": [
                {"name": "...", "price": {"value": 3.5}, "status": "AVAILABLE"}
              ]
            }
          ]
        }
        """
        body = dict(item)
        body.setdefault("categoryId", category_id)
        return await self._client.request(
            "PUT",
            self._p(f"/merchants/{merchant_id}/items"),
            json=body,
        )

    async def patch_item(
        self,
        merchant_id: str,
        item_id: str,
        *,
        patch: dict[str, Any],
    ) -> dict[str, Any] | None:
        """PATCH /items/{itemId} — JSON Merge Patch parcial.

        `patch` deve conter só campos a atualizar (ex: {"price": {"value": 9.9}}
        ou {"status": "UNAVAILABLE"}). Substitui /items/status e /items/price
        deprecated.
        """
        return await self._client.request(
            "PATCH",
            self._p(f"/merchants/{merchant_id}/items/{item_id}"),
            json=patch,
        )

    async def delete_item(
        self, merchant_id: str, category_id: str, product_id: str
    ) -> None:
        """Remove item (slot de product em category). Path usa productId."""
        await self._client.request(
            "DELETE",
            self._p(
                f"/merchants/{merchant_id}/categories/{category_id}"
                f"/products/{product_id}"
            ),
        )

    # ----- Helpers convenientes (compat com callers antigos) -----
    async def update_item_status(
        self, merchant_id: str, item_id: str, status: str
    ) -> dict[str, Any] | None:
        """Atalho: PATCH /items/{id} com {status}. Endpoint batch deprecated."""
        return await self.patch_item(
            merchant_id, item_id, patch={"status": status}
        )

    async def update_item_price(
        self, merchant_id: str, item_id: str, price: float
    ) -> dict[str, Any] | None:
        """Atalho: PATCH /items/{id} com {price}."""
        return await self.patch_item(
            merchant_id, item_id, patch={"price": {"value": float(price)}}
        )

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
        """Atalho: PATCH /items/{id} — campos básicos do product associado.

        nome/descrição/foto são propriedades do Product, e o merge patch no
        endpoint /items/{id} aceita-os via product inline.
        """
        patch: dict[str, Any] = {}
        product: dict[str, Any] = {}
        if name is not None:
            product["name"] = name
        if description is not None:
            product["description"] = description
        if image_path is not None:
            product["imagePath"] = image_path
        if external_code is not None:
            patch["externalCode"] = external_code
        if product:
            patch["product"] = product
        if not patch:
            return None
        return await self.patch_item(merchant_id, item_id, patch=patch)

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
        """Atalho: upsert_item com payload mínimo (product inline)."""
        product: dict[str, Any] = {"name": name}
        if description:
            product["description"] = description
        if image_path:
            product["imagePath"] = image_path
        item: dict[str, Any] = {
            "categoryId": category_id,
            "product": product,
            "price": {"value": float(price)},
            "status": status,
        }
        if external_code:
            item["externalCode"] = external_code
        return await self.upsert_item(
            merchant_id, category_id=category_id, item=item
        )

    # =========================================================================
    # Option Group  (camelCase!)
    # =========================================================================
    async def list_option_groups(
        self, merchant_id: str
    ) -> list[dict[str, Any]]:
        path = self._p(f"/merchants/{merchant_id}/optionGroups")
        result = await self._client.get(path)
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            return result.get("optionGroups", [])
        return []

    async def update_option_group(
        self,
        merchant_id: str,
        option_group_id: str,
        *,
        name: str | None = None,
        min_choices: int | None = None,
        max_choices: int | None = None,
        external_code: str | None = None,
    ) -> dict[str, Any] | None:
        body: dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if min_choices is not None:
            body["min"] = int(min_choices)
        if max_choices is not None:
            body["max"] = int(max_choices)
        if external_code is not None:
            body["externalCode"] = external_code
        return await self._client.request(
            "PATCH",
            self._p(f"/merchants/{merchant_id}/optionGroups/{option_group_id}"),
            json=body,
        )

    async def update_option_group_status(
        self, merchant_id: str, option_group_id: str, status: str
    ) -> dict[str, Any] | None:
        """Pausa/ativa grupo de complementos inteiro."""
        return await self._client.request(
            "PATCH",
            self._p(
                f"/merchants/{merchant_id}/optionGroups/{option_group_id}/status"
            ),
            json={"status": status},
        )

    async def delete_option_group(
        self, merchant_id: str, option_group_id: str
    ) -> None:
        await self._client.request(
            "DELETE",
            self._p(f"/merchants/{merchant_id}/optionGroups/{option_group_id}"),
        )

    async def disassociate_option_group_from_product(
        self, merchant_id: str, option_group_id: str, product_id: str
    ) -> None:
        """Desliga um optionGroup de um product específico."""
        await self._client.request(
            "DELETE",
            self._p(
                f"/merchants/{merchant_id}/optionGroups/{option_group_id}"
                f"/products/{product_id}"
            ),
        )

    # =========================================================================
    # Option (complementos)
    # =========================================================================
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
        """POST /optionGroups/{ogId}/options — cria option dentro de grupo."""
        product: dict[str, Any] = {"name": name}
        if image_path:
            product["imagePath"] = image_path
        body: dict[str, Any] = {
            "product": product,
            "price": {"value": float(price)},
            "status": status,
        }
        if external_code:
            body["externalCode"] = external_code
        return await self._client.post(
            self._p(
                f"/merchants/{merchant_id}/optionGroups/{option_group_id}/options"
            ),
            json=body,
        )

    async def delete_option(
        self,
        merchant_id: str,
        option_group_id: str,
        product_id: str,
    ) -> None:
        """DELETE /optionGroups/{ogId}/products/{productId}/option."""
        await self._client.request(
            "DELETE",
            self._p(
                f"/merchants/{merchant_id}/optionGroups/{option_group_id}"
                f"/products/{product_id}/option"
            ),
        )

    async def batch_update_options_price(
        self, merchant_id: str, updates: list[dict[str, Any]]
    ) -> dict[str, Any] | None:
        """PATCH /options/price — batch. updates=[{optionId,price:{value:X}},...]"""
        return await self._client.request(
            "PATCH",
            self._p(f"/merchants/{merchant_id}/options/price"),
            json=updates,
        )

    async def batch_update_options_status(
        self, merchant_id: str, updates: list[dict[str, str]]
    ) -> dict[str, Any] | None:
        """PATCH /options/status — batch. updates=[{optionId,status:X},...]"""
        return await self._client.request(
            "PATCH",
            self._p(f"/merchants/{merchant_id}/options/status"),
            json=updates,
        )

    async def batch_update_options_external_code(
        self, merchant_id: str, updates: list[dict[str, str]]
    ) -> dict[str, Any] | None:
        return await self._client.request(
            "PATCH",
            self._p(f"/merchants/{merchant_id}/options/externalCode"),
            json=updates,
        )

    # ----- Atalhos compat -----
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
        """Compat: usa batch endpoints. Não existe PATCH /options/{id} single.

        Como /options/price e /options/status só atualizam price/status, o
        rename (name) e imagePath têm que ser feitos via PUT /items
        reenviando item completo. Aqui só roteamos price+status.
        """
        results: list[Any] = []
        if price is not None:
            results.append(
                await self.batch_update_options_price(
                    merchant_id,
                    [{"optionId": option_id, "price": {"value": float(price)}}],
                )
            )
        if status is not None:
            results.append(
                await self.batch_update_options_status(
                    merchant_id, [{"optionId": option_id, "status": status}]
                )
            )
        # name/image_path não suportados aqui — caller precisa usar upsert_item
        return results[-1] if results else None

    async def list_inventory(
        self, merchant_id: str, product_id: str
    ) -> dict[str, Any]:
        return await self._client.get(
            self._p(f"/merchants/{merchant_id}/inventory/{product_id}")
        )

    async def upsert_inventory(
        self,
        merchant_id: str,
        product_id: str,
        quantity: int,
    ) -> dict[str, Any] | None:
        return await self._client.post(
            self._p(f"/merchants/{merchant_id}/inventory"),
            json={"productId": product_id, "quantity": int(quantity)},
        )

    # =========================================================================
    # Image upload
    # =========================================================================
    async def upload_image(
        self,
        merchant_id: str,
        image_bytes: bytes,
        content_type: str = "image/jpeg",
    ) -> dict[str, Any] | None:
        """POST /image/upload — multipart/form-data. Retorna {path: '...'}."""
        import httpx

        path = self._p(f"/merchants/{merchant_id}/image/upload")
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

    # =========================================================================
    # Batch result
    # =========================================================================
    async def get_batch_result(
        self, merchant_id: str, batch_id: str
    ) -> dict[str, Any]:
        """Resultado de operações em batch."""
        return await self._client.get(
            self._p(f"/merchants/{merchant_id}/batch/{batch_id}")
        )

    # =========================================================================
    # Version (upgrade/downgrade catalog version)
    # =========================================================================
    async def upgrade_to_v2(self, merchant_id: str) -> dict[str, Any] | None:
        return await self._client.post(
            self._p(f"/merchants/{merchant_id}/version/upgrade")
        )

    async def downgrade_to_v1(self, merchant_id: str) -> dict[str, Any] | None:
        return await self._client.post(
            self._p(f"/merchants/{merchant_id}/version/downgrade")
        )
