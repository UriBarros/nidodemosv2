"""Página de pedidos."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from dashboard.auth import render_sidebar_user, require_auth  # noqa: E402
from dashboard.lib import api_get, check_api_health, merchant_selector  # noqa: E402

st.set_page_config(page_title="Pedidos | gtrifood", page_icon="🛒", layout="wide")
st.title("Pedidos")

if not check_api_health():
    st.stop()

render_sidebar_user()
require_auth()

# --- Filtros ---
with st.sidebar:
    st.header("Filtros")
    sel = merchant_selector()
    merchant_id = sel[0] if sel else None

    status_filter = st.selectbox(
        "Status",
        ["(todos)", "PLACED", "CONFIRMED", "DISPATCHED", "CONCLUDED", "CANCELLED"],
    )
    status_param = None if status_filter == "(todos)" else status_filter

    limit = st.slider("Limite", min_value=10, max_value=500, value=100, step=10)

# --- Lista ---
params: dict = {"limit": limit}
if merchant_id:
    params["merchant_id"] = merchant_id
if status_param:
    params["status"] = status_param

try:
    orders = api_get("/orders", params=params)
except Exception as e:
    st.error(f"Erro ao buscar pedidos: {e}")
    st.stop()

if not orders:
    st.info("Nenhum pedido encontrado com esses filtros.")
    st.stop()

df = pd.DataFrame(orders)

# Métricas resumidas
col1, col2, col3 = st.columns(3)
col1.metric("Total exibido", len(df))
col2.metric("Valor total", f"R$ {df['total_amount'].astype(float).sum():,.2f}")
col3.metric("Ticket médio", f"R$ {df['total_amount'].astype(float).mean():,.2f}")

st.divider()

# Tabela
display_cols = [
    "display_id",
    "status",
    "order_type",
    "total_amount",
    "customer_name",
    "created_at_ifood",
    "synced_at",
]
df_display = df[display_cols].copy()
df_display = df_display.rename(
    columns={
        "display_id": "Nº",
        "status": "Status",
        "order_type": "Tipo",
        "total_amount": "Total (R$)",
        "customer_name": "Cliente",
        "created_at_ifood": "Criado",
        "synced_at": "Sincronizado",
    }
)
st.dataframe(df_display, use_container_width=True, hide_index=True)
