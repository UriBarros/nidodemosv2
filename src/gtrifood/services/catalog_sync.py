"""Sincroniza cardápio (categorias + itens) do iFood pra tabelas locais.

Usado pelo endpoint POST /catalog/sync?merchant_id=X.
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
    """Sincroniza catálogo de um merchant (1 = primeiro catálogo retornado).

    Retorna dict com counts: { categories: N, items: M }.
    """
    async with get_session() as session:
        result = await session.execute(
            select(Merchant.tenant_id, Merchant.ifood_merchant_id, Merchant.client_id)
            .where(Merchant.id == merchant_id)
        )
        row = result.first()
        if not row:
            raise ValueError(f"merchant {merchant_id} não encontrado")
        tenant_id, ifood_merchant_id, client_id = row

    # Escolhe token_provider: client (Distribuída) ou client_credentials (Centralizada)
    if client_id:
        from gtrifood.services.client_tokens import get_or_refresh_access_token

        async def _tp() -> str:
            return await get_or_refresh_access_token(client_id)

        ifood = IFoodClient(token_provider=_tp)
    else:
        ifood = IFoodClient()

    api = CatalogAPI(ifood)

    # 1. Lista catálogos. Usa o primeiro (apps de loja real costumam ter 1).
    catalogs = await api.list_catalogs(ifood_merchant_id)
    if not catalogs:
        logger.warning("nenhum_catalog_no_ifood", merchant_id=str(merchant_id))
        return {"categories": 0, "items": 0}

    catalog_id = catalogs[0].get("catalogId") or catalogs[0].get("id")
    if not catalog_id:
        logger.error("catalog_sem_id", merchant_id=str(merchant_id), payload=catalogs[0])
        return {"categories": 0, "items": 0}

    # 2. Lista categorias (com items embutidos)
    try:
        categories = await api.list_categories(
            ifood_merchant_id, catalog_id, include_items=True
        )
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
        # Cache: ifood_category_id -> local category UUID
        category_map: dict[str, uuid.UUID] = {}

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
            category_map[ifood_cat_id] = cat_id_local
            cat_count += 1

            # Itens embutidos
            for item in cat.get("items", []) or []:
                item_count += await _upsert_item(
                    session,
                    tenant_id=tenant_id,
                    merchant_id=merchant_id,
                    category_id=cat_id_local,
                    item=item,
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
    item: dict[str, Any],
) -> int:
    """UPSERT de um item. Retorna 1 se persistiu, 0 se ignorado."""
    ifood_item_id = item.get("id") or item.get("itemId")
    if not ifood_item_id:
        return 0

    price_obj = item.get("price") or {}
    price = price_obj.get("value") if isinstance(price_obj, dict) else price_obj
    original = price_obj.get("originalValue") if isinstance(price_obj, dict) else None

    stmt = insert(CatalogItem).values(
        tenant_id=tenant_id,
        merchant_id=merchant_id,
        category_id=category_id,
        ifood_item_id=ifood_item_id,
        ifood_product_id=item.get("productId"),
        name=item.get("name") or ifood_item_id,
        description=item.get("description"),
        external_code=item.get("externalCode"),
        price=Decimal(str(price)) if price is not None else None,
        original_price=Decimal(str(original)) if original is not None else None,
        status=(item.get("status") or "AVAILABLE").upper(),
        image_path=item.get("imagePath"),
        raw_data=item,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["tenant_id", "ifood_item_id"],
        set_={
            "category_id": stmt.excluded.category_id,
            "name": stmt.excluded.name,
            "description": stmt.excluded.description,
            "external_code": stmt.excluded.external_code,
            "price": stmt.excluded.price,
            "original_price": stmt.excluded.original_price,
            "status": stmt.excluded.status,
            "image_path": stmt.excluded.image_path,
            "raw_data": stmt.excluded.raw_data,
        },
    )
    await session.execute(stmt)
    return 1
