"""Sync financeiro — vendas, antecipações, ocorrências.

Roda periodicamente (ex: diariamente) por período.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select

from gtrifood.core.db import get_session
from gtrifood.core.logging import get_logger
from gtrifood.integrations.ifood.client import IFoodAPIError, IFoodClient
from gtrifood.integrations.ifood.financial import FinancialAPI
from gtrifood.models.db import FinancialEvent, Merchant

logger = get_logger(__name__)


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _safe_decimal(value: object) -> Decimal:
    if value is None:
        return Decimal(0)
    try:
        return Decimal(str(value))
    except (ValueError, TypeError):
        return Decimal(0)


async def sync_financial_for_merchant(
    tenant_id: uuid.UUID,
    merchant_id: uuid.UUID,
    *,
    days_back: int = 30,
) -> int:
    """Busca financeiro dos últimos N dias e persiste. Retorna quantos eventos novos."""
    end = date.today()
    begin = end - timedelta(days=days_back)

    async with get_session() as session:
        merchant = (
            await session.execute(select(Merchant).where(Merchant.id == merchant_id))
        ).scalar_one_or_none()
        if not merchant:
            raise ValueError(f"Merchant {merchant_id} não encontrado")
        ifood_id = merchant.ifood_merchant_id

    api = FinancialAPI(IFoodClient())

    async def _safe_fetch(coro_factory, kind: str) -> list:
        """Captura 4xx do iFood — comum em sandbox/teste."""
        try:
            return await coro_factory()
        except IFoodAPIError as e:
            if 400 <= e.status_code < 500:
                logger.warning(
                    "financial_endpoint_indisponivel",
                    kind=kind,
                    status=e.status_code,
                    merchant_id=str(merchant_id),
                )
                return []
            raise

    sales = await _safe_fetch(lambda: api.list_sales(ifood_id, begin, end), "sales")
    anticipations = await _safe_fetch(
        lambda: api.list_anticipations(ifood_id, begin, end), "anticipations"
    )
    occurrences = await _safe_fetch(
        lambda: api.list_occurrences(ifood_id, begin, end), "occurrences"
    )

    inserted = 0
    async with get_session() as session:
        for item in sales:
            session.add(
                FinancialEvent(
                    tenant_id=tenant_id,
                    merchant_id=merchant_id,
                    ifood_reference_id=item.get("id"),
                    event_type="SALE",
                    competence_date=_parse_date(item.get("paymentDate") or item.get("date")),
                    amount=_safe_decimal(item.get("value") or item.get("amount")),
                    description=item.get("description"),
                    raw_data=item,
                )
            )
            inserted += 1
        for item in anticipations:
            session.add(
                FinancialEvent(
                    tenant_id=tenant_id,
                    merchant_id=merchant_id,
                    ifood_reference_id=item.get("id"),
                    event_type="ANTICIPATION",
                    competence_date=_parse_date(item.get("anticipationDate")),
                    amount=_safe_decimal(item.get("amount") or item.get("value")),
                    description=item.get("description"),
                    raw_data=item,
                )
            )
            inserted += 1
        for item in occurrences:
            session.add(
                FinancialEvent(
                    tenant_id=tenant_id,
                    merchant_id=merchant_id,
                    ifood_reference_id=item.get("id"),
                    event_type="OCCURRENCE",
                    competence_date=_parse_date(item.get("occurrenceDate") or item.get("date")),
                    amount=_safe_decimal(item.get("amount") or item.get("value")),
                    description=item.get("description"),
                    raw_data=item,
                )
            )
            inserted += 1

    logger.info(
        "financeiro_sincronizado",
        merchant_id=str(merchant_id),
        sales=len(sales),
        anticipations=len(anticipations),
        occurrences=len(occurrences),
    )
    return inserted
