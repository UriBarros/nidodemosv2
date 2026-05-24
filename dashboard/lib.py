"""Helpers compartilhados pelo dashboard Streamlit."""

from __future__ import annotations

import os
from typing import Any

import httpx
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


@st.cache_data(ttl=30)
def api_get(path: str, params: dict[str, Any] | None = None) -> Any:
    """GET na API com cache de 30s."""
    url = f"{API_BASE_URL}{path}"
    response = httpx.get(url, params=params, timeout=30.0)
    response.raise_for_status()
    return response.json()


def api_post(path: str, json_body: Any = None, params: dict[str, Any] | None = None) -> Any:
    """POST na API (sem cache)."""
    url = f"{API_BASE_URL}{path}"
    response = httpx.post(url, json=json_body, params=params, timeout=120.0)
    response.raise_for_status()
    return response.json() if response.content else None


def merchant_selector(label: str = "Merchant") -> tuple[str, str] | None:
    """Selectbox de merchants. Retorna (id, name) ou None se vazio."""
    try:
        merchants = api_get("/merchants")
    except Exception as e:
        st.error(f"Falha ao buscar merchants: {e}")
        return None

    if not merchants:
        st.warning("Nenhum merchant ainda. Use 'Sincronizar merchants' na home.")
        return None

    options = {m["name"]: m["id"] for m in merchants}
    selected_name = st.selectbox(label, list(options.keys()))
    return options[selected_name], selected_name


def check_api_health() -> bool:
    """True se API responde. Mostra erro visual se não."""
    try:
        health = api_get("/health")
        return health.get("status") == "ok"
    except Exception as e:
        st.error(
            f"❌ API offline em {API_BASE_URL}. "
            f"Rode em outro terminal: `uvicorn gtrifood.api.main:app --reload`\n\nErro: {e}"
        )
        return False
