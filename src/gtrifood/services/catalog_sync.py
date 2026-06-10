"""Sincroniza cardápio (categorias + itens) do iFood — Catalog API v2.0.

Estratégia (atualizada):
1. GET /catalog/v2.0/merchants/{id}/categories?includeItems=true
2. Pra cada categoria: UPSERT em catalog_categories
3. Pra cada item embutido: UPSERT em catalog_items (raw_data completa)

UPSERT idempotente por (tenant_id, ifood_*_id).
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from gtrifood.core.db import get_session
from gtrifood.core.logging import get_logger
from gtrifood.integrations.ifood.catalog import CatalogAPI
from gtrifood.integrations.ifood.client import IFoodAPIError, IFoodClient
from gtrifood.models.db import CatalogCategory, CatalogItem, Merchant

logger = get_logger(__name__)


async def sync_catalog_for_merchant(merchant_id: uuid.UUID) -> dict[str, int]:
    """Sincroniza catálogo de um merchant.

    Retorna dict com counts: {categories: N, items: M}.
    """
    async with get_session() as session:
        result = await session.execute(
            select(
                Merchant.tenant_id, Merchant.ifood_merchant_id, Merchant.client_id
            ).where(Merchant.id == merchant_id)
        )
        row = result.first()
        if not row:
            raise ValueError(f"merchant {merchant_id} não encontrado")
        tenant_id, ifood_merchant_id, client_id = row

    # Token correto
    if client_id:
        from gtrifood.services.client_tokens import get_or_refresh_access_token

        async def _tp() -> str:
            return await get_or_refresh_access_token(client_id)

        ifood = IFoodClient(token_provider=_tp)
    else:
        ifood = IFoodClient()

    api = CatalogAPI(ifood)

    # Catalog ID (raramente usado, mas mantemos referência)
    catalog_id = ""
    try:
        catalogs = await api.list_catalogs(ifood_merchant_id)
        if catalogs:
            catalog_id = catalogs[0].get("catalogId") or catalogs[0].get("id", "")
    except IFoodAPIError as e:
        logger.warning("list_catalogs_falhou", status=e.status_code)

    # Lista categorias com items embutidos
    try:
        categories = await api.list_categories(ifood_merchant_id, include_items=True)
    except IFoodAPIError as e:
        logger.error(
            "catalog_categories_falhou",
            merchant_id=str(merchant_id),
            status=e.status_code,
        )
        return {"categories": 0, "items": 0}

    cat_count = 0
    item_count = 0

    async with get_session() as session:
        for seq, cat in enumerate(categories):
            ifood_cat_id = cat.get("id") or cat.get("categoryId")
            if not ifood_cat_id:
                continue

            cat_stmt = insert(CatalogCategory).values(
                tenant_id=tenant_id,
                merchant_id=merchant_id,
                ifood_catalog_id=catalog_id,
                ifood_category_id=ifood_cat_id,
                name=cat.get("name") or ifood_cat_id,
                external_code=cat.get("externalCode"),
                status=cat.get("status") or "AVAILABLE",
                sequence=cat.get("sequence", seq),
                raw_data=cat,
            )
            cat_stmt = cat_stmt.on_conflict_do_update(
                index_elements=["tenant_id", "ifood_category_id"],
                set_={
                    "name": cat_stmt.excluded.name,
                    "external_code": cat_stmt.excluded.external_code,
                    "status": cat_stmt.excluded.status,
                    "sequence": cat_stmt.excluded.sequence,
                    "raw_data": cat_stmt.excluded.raw_data,
                },
            ).returning(CatalogCategory.id)
            cat_id_local = (await session.execute(cat_stmt)).scalar_one()
            cat_count += 1

            # Items da categoria
            for item in cat.get("items", []) or []:
                item_count += await _upsert_item(
                    session,
                    tenant_id=tenant_id,
                    merchant_id=merchant_id,
                    category_id=cat_id_local,
                    item_payload=item,
                )

    logger.info(
        "catalog_sincronizado",
        merchant_id=str(merchant_id),
        categories=cat_count,
        items=item_count,
    )
    return {"categories": cat_count, "items": item_count}


async def _upsert_item(
    session,
    tenant_id: uuid.UUID,
    merchant_id: uuid.UUID,
    category_id: uuid.UUID,
    item_payload: dict[str, Any],
) -> int:
    """UPSERT de um item.

    Aceita 2 formatos do iFood:
    - Flat: {id, name, price: {value}, ...} (legado)
    - Nested: {item: {id, price, ...}, products: [{name, description}], ...} (v2.0)
    """
    # Detecta estrutura nested vs flat
    if "item" in item_payload and isinstance(item_payload["item"], dict):
        # Nested (v2.0)
        item_meta = item_payload["item"]
        products = item_payload.get("products", [])
        product = products[0] if products else {}
        ifood_item_id = item_meta.get("id")
        name = product.get("name") or item_meta.get("name") or ifood_item_id
        description = product.get("description")
        price = (item_meta.get("price") or {}).get("value")
        status = item_meta.get("status", "AVAILABLE")
        external_code = item_meta.get("externalCode")
        image_path = item_meta.get("imagePath") or product.get("imagePath")
        product_id = product.get("id")
    else:
        # Flat (legado)
        ifood_item_id = item_payload.get("id") or item_payload.get("itemId")
        name = item_payload.get("name") or ifood_item_id
        description = item_payload.get("description")
        price_obj = item_payload.get("price") or {}
        price = (
            price_obj.get("value") if isinstance(price_obj, dict) else price_obj
        )
        status = (item_payload.get("status") or "AVAILABLE").upper()
        external_code = item_payload.get("externalCode")
        image_path = item_payload.get("imagePath")
        product_id = item_payload.get("productId")

    if not ifood_item_id:
        return 0

    stmt = insert(CatalogItem).values(
        tenant_id=tenant_id,
        merchant_id=merchant_id,
        category_id=category_id,
        ifood_item_id=ifood_item_id,
        ifood_product_id=product_id,
        name=name,
        description=description,
        external_code=external_code,
        price=Decimal(str(price)) if price is not None else None,
        original_price=None,
        status=(status or "AVAILABLE").upper(),
        image_path=image_path,
        raw_data=item_payload,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["tenant_id", "ifood_item_id"],
        set_={
            "category_id": stmt.excluded.category_id,
            "name": stmt.excluded.name,
            "description": stmt.excluded.description,
            "external_code": stmt.excluded.external_code,
            "price": stmt.excluded.price,
            "status": stmt.excluded.status,
            "image_path": stmt.excluded.image_path,
            "raw_data": stmt.excluded.raw_data,
        },
    )
    await session.execute(stmt)
    return 1
