"""Endpoints do módulo Financial v3 da API iFood.

Cobertura básica: vendas (sales), antecipações (anticipations), ocorrências.
Períodos sempre em formato ISO 8601 date (YYYY-MM-DD).
"""

from __future__ import annotations

from datetime import date
from typing import Any

from gtrifood.integrations.ifood.client import IFoodClient


class FinancialAPI:
    def __init__(self, client: IFoodClient) -> None:
        self._client = client

    async def list_sales(
        self,
        merchant_id: str,
        begin: date,
        end: date,
    ) -> list[dict[str, Any]]:
        """Lista vendas de um merchant em um período."""
        params = {
            "beginPaymentDate": begin.isoformat(),
            "endPaymentDate": end.isoformat(),
        }
        result = await self._client.get(
            f"/financial-v3.0/merchants/{merchant_id}/sales",
            params=params,
        )
        return result.get("sales", []) if isinstance(result, dict) else (result or [])

    async def list_anticipations(
        self,
        merchant_id: str,
        begin: date,
        end: date,
    ) -> list[dict[str, Any]]:
        """Antecipações realizadas no período."""
        params = {"beginAnticipationDate": begin.isoformat(), "endAnticipationDate": end.isoformat()}
        result = await self._client.get(
            f"/financial-v3.0/merchants/{merchant_id}/anticipations",
            params=params,
        )
        return result.get("anticipations", []) if isinstance(result, dict) else (result or [])

    async def list_occurrences(
        self,
        merchant_id: str,
        begin: date,
        end: date,
    ) -> list[dict[str, Any]]:
        """Ocorrências (ajustes, débitos, créditos pontuais)."""
        params = {"beginOccurrenceDate": begin.isoformat(), "endOccurrenceDate": end.isoformat()}
        result = await self._client.get(
            f"/financial-v3.0/merchants/{merchant_id}/occurrences",
            params=params,
        )
        return result.get("occurrences", []) if isinstance(result, dict) else (result or [])
