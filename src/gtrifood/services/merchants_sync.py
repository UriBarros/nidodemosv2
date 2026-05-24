"""Sincroniza merchants do iFood pra tabela `merchants`.

Idempotente: UPSERT por (tenant_id, ifood_merchant_id).
Pra app de teste só haverá 1 merchant fictício.
"""

from __future__ import annotations

import uuid

from sqlalchemy.dialects.postgresql import insert

from gtrifood.core.db import get_session
from gtrifood.core.logging import get_logger
from gtrifood.integrations.ifood.client import IFoodAPIError, IFoodClient
from gtrifood.integrations.ifood.merchants import MerchantAPI
from gtrifood.models.db import Merchant

logger = get_logger(__name__)


async def sync_merchants_for_tenant(tenant_id: uuid.UUID) -> int:
    """Busca merchants no iFood e UPSERT no banco. Retorna quantos persistidos.

    Estratégia: usa dados do GET /merchants (lista). Tenta enriquecer com
    GET /merchants/{id}, mas se falhar (ex: 404 no app de teste) usa só os dados
    da lista.
    """
    api = MerchantAPI(IFoodClient())
    raw_merchants = await api.list_merchants()

    if not raw_merchants:
        logger.warning("nenhum_merchant_no_ifood", tenant_id=str(tenant_id))
        return 0

    async with get_session() as session:
        for m in raw_merchants:
            ifood_id = m["id"]
            details: dict = dict(m)  # começa com dados da lista
            try:
                details.update(await api.get_merchant(ifood_id))
            except IFoodAPIError as e:
                logger.warning(
                    "merchant_details_indisponivel",
                    ifood_id=ifood_id,
                    status=e.status_code,
                )

            stmt = insert(Merchant).values(
                tenant_id=tenant_id,
                ifood_merchant_id=ifood_id,
                name=details.get("name") or ifood_id,
                corporate_name=details.get("corporateName"),
                cnpj=(details.get("cnpj") or "").strip() or None,
                status="active",
                raw_data=details,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["tenant_id", "ifood_merchant_id"],
                set_={
                    "name": stmt.excluded.name,
                    "corporate_name": stmt.excluded.corporate_name,
                    "cnpj": stmt.excluded.cnpj,
                    "raw_data": stmt.excluded.raw_data,
                },
            )
            await session.execute(stmt)

    logger.info("merchants_sincronizados", tenant_id=str(tenant_id), count=len(raw_merchants))
    return len(raw_merchants)
