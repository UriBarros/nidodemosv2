"""gtrifood — Dashboard Streamlit (home).

Rodar:
    streamlit run dashboard/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st  # noqa: E402

from dashboard.auth import (  # noqa: E402
    is_authenticated,
    render_login_form,
    render_sidebar_user,
)
from dashboard.lib import api_get, api_post, check_api_health  # noqa: E402
from dashboard.theme import apply_theme  # noqa: E402

st.set_page_config(
    page_title="gtrifood",
    page_icon="🍔",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_theme()

st.title("gtrifood")
st.caption("Painel de dados iFood Developer — dados unificados de pedidos, financeiro e reviews.")

if not check_api_health():
    st.stop()

render_sidebar_user()

# --- Gate de auth ---
if not is_authenticated():
    render_login_form()
    st.stop()

st.divider()

# --- Resumo geral ---
col1, col2, col3, col4 = st.columns(4)

try:
    merchants = api_get("/merchants")
    col1.metric("Merchants", len(merchants))
except Exception:
    col1.metric("Merchants", "?")

try:
    orders_count = api_get("/orders/count")
    col2.metric("Pedidos", orders_count["count"])
except Exception:
    col2.metric("Pedidos", "?")

try:
    placed_count = api_get("/orders/count", params={"status": "PLACED"})
    col3.metric("Em aberto (PLACED)", placed_count["count"])
except Exception:
    col3.metric("Em aberto", "?")

try:
    fin_summary = api_get("/financial/summary")
    total_sales = fin_summary.get("SALE", 0)
    col4.metric("Vendas (total)", f"R$ {total_sales:,.2f}")
except Exception:
    col4.metric("Vendas", "?")

st.divider()

# --- Ações rápidas ---
st.subheader("Ações")

col_a, col_b = st.columns(2)

with col_a:
    if st.button("🔄 Sincronizar merchants", use_container_width=True):
        with st.spinner("Sincronizando merchants do iFood..."):
            try:
                result = api_post("/merchants/sync")
                st.success(result["message"])
                st.cache_data.clear()
            except Exception as e:
                st.error(f"Erro: {e}")

with col_b:
    st.info(
        "💡 **Pedidos sincronizam automaticamente** pelo worker de polling.\n\n"
        "Rode `python scripts/run_poller.py` em outro terminal."
    )

st.divider()

st.markdown(
    """
    ### Navegação

    Use o menu lateral pra acessar:
    - **Pedidos** — lista de pedidos sincronizados, filtros por status e merchant
    - **Financeiro** — vendas, antecipações, ocorrências
    - **Reviews** — avaliações dos clientes
    """
)
