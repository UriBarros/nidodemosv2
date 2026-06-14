"""iFood Financial API v3.0 — conciliação, repasses, vendas e eventos.

Server base: https://merchant-api.ifood.com.br/financial/v3.0/

Endpoints (jun/2026):
- GET  /merchants/{m}/reconciliation                  conciliação consolidada
- GET  /merchants/{m}/settlements                     repasses do período
- GET  /merchants/{m}/anticipations                   antecipações
- GET  /merchants/{m}/sales                           vendas
- GET  /merchants/{m}/financial-events                eventos (taxas/ajustes)
- POST /merchants/{m}/reconciliation/on-demand        agenda geração arquivo
- GET  /merchants/{m}/reconciliation/on-demand/{rid}  baixa arquivo gerado

Mudanças vs v3 antiga: /occurrences foi removido (substituído por
/financial-events). Períodos sempre ISO 8601 (YYYY-MM-DD).
"""

from __future__ import annotations

from datetime import date
from typing import Any

from gtrifood.integrations.ifood.client import IFoodClient


class FinancialAPI:
    """Wrapper do Financial API v3.0."""

    BASE = "/financial/v3.0"

    def __init__(self, client: IFoodClient) -> None:
        self._client = client

    def _p(self, path: str) -> str:
        return f"{self.BASE}{path}"

    @staticmethod
    def _unwrap(result: Any, key: str) -> list[dict[str, Any]]:
        """Aceita resposta como list direta ou dict {key: [...]}."""
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            return result.get(key) or []
        return []

    # =========================================================================
    # Conciliação
    # =========================================================================
    async def get_reconciliation(
        self,
        merchant_id: str,
        begin: date,
        end: date,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Conciliação consolidada do período (taxas, ajustes, líquido)."""
        params = {
            "beginCompetenceDate": begin.isoformat(),
            "endCompetenceDate": end.isoformat(),
        }
        return await self._client.get(
            self._p(f"/merchants/{merchant_id}/reconciliation"),
            params=params,
        )

    async def request_reconciliation_on_demand(
        self,
        merchant_id: str,
        begin: date,
        end: date,
    ) -> dict[str, Any] | None:
        """Agenda geração de arquivo de conciliação on demand.

        Retorna {requestId: '...'} usado depois em fetch_reconciliation_file.
        """
        return await self._client.post(
            self._p(f"/merchants/{merchant_id}/reconciliation/on-demand"),
            json={
                "beginCompetenceDate": begin.isoformat(),
                "endCompetenceDate": end.isoformat(),
            },
        )

    async def fetch_reconciliation_file(
        self, merchant_id: str, request_id: str
    ) -> dict[str, Any]:
        """Busca metadados/URL do arquivo gerado pelo on-demand request."""
        return await self._client.get(
            self._p(
                f"/merchants/{merchant_id}/reconciliation/on-demand/{request_id}"
            )
        )

    # =========================================================================
    # Settlements (repasses)
    # =========================================================================
    async def list_settlements(
        self,
        merchant_id: str,
        begin: date,
        end: date,
    ) -> list[dict[str, Any]]:
        """Lista repasses pagos pelo iFood no período."""
        params = {
            "beginSettlementDate": begin.isoformat(),
            "endSettlementDate": end.isoformat(),
        }
        result = await self._client.get(
            self._p(f"/merchants/{merchant_id}/settlements"),
            params=params,
        )
        return self._unwrap(result, "settlements")

    # =========================================================================
    # Anticipations
    # =========================================================================
    async def list_anticipations(
        self,
        merchant_id: str,
        begin: date,
        end: date,
    ) -> list[dict[str, Any]]:
        params = {
            "beginAnticipationDate": begin.isoformat(),
            "endAnticipationDate": end.isoformat(),
        }
        result = await self._client.get(
            self._p(f"/merchants/{merchant_id}/anticipations"),
            params=params,
        )
        return self._unwrap(result, "anticipations")

    # =========================================================================
    # Sales
    # =========================================================================
    async def list_sales(
        self,
        merchant_id: str,
        begin: date,
        end: date,
    ) -> list[dict[str, Any]]:
        params = {
            "beginPaymentDate": begin.isoformat(),
            "endPaymentDate": end.isoformat(),
        }
        result = await self._client.get(
            self._p(f"/merchants/{merchant_id}/sales"),
            params=params,
        )
        return self._unwrap(result, "sales")

    # =========================================================================
    # Financial events  (substitui /occurrences da v3 antiga)
    # =========================================================================
    async def list_financial_events(
        self,
        merchant_id: str,
        begin: date,
        end: date,
    ) -> list[dict[str, Any]]:
        """Eventos financeiros: taxas, ajustes, créditos, débitos."""
        params = {
            "beginEventDate": begin.isoformat(),
            "endEventDate": end.isoformat(),
        }
        result = await self._client.get(
            self._p(f"/merchants/{merchant_id}/financial-events"),
            params=params,
        )
        return self._unwrap(result, "financialEvents")

    # ----- Alias compat (caller antigo chamava list_occurrences) -----
    async def list_occurrences(
        self,
        merchant_id: str,
        begin: date,
        end: date,
    ) -> list[dict[str, Any]]:
        """DEPRECATED: /occurrences foi removido. Redireciona pra
        list_financial_events."""
        return await self.list_financial_events(merchant_id, begin, end)
