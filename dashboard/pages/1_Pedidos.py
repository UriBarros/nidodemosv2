"""Página de pedidos."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from dashboard.auth import render_sidebar_user, require_auth  # noqa: E402
from dashboard.lib import api_get, api_post, check_api_health, merchant_selector  # noqa: E402
from dashboard.theme import apply_theme  # noqa: E402

st.set_page_config(page_title="Pedidos | gtrifood", page_icon="🛒", layout="wide")
apply_theme()
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
        [
            "(todos)",
            "PLACED",
            "CONFIRMED",
            "READY_FOR_PICKUP",
            "DISPATCHED",
            "ARRIVED",
            "CONCLUDED",
            "CANCELLATION_REQUESTED",
            "CANCELLATION_REQUEST_ACCEPTED",
            "CANCELLATION_REQUEST_DENIED",
            "CANCELLED",
        ],
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
    "updated_at",
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
        "updated_at": "Atualizado",
    }
)
st.dataframe(df_display, use_container_width=True, hide_index=True)

# --- Timeline de um pedido ---
st.divider()
st.subheader("Timeline de eventos")

order_options = {f"{r['display_id']} — {r['status']}": r["id"] for r in orders}
chosen = st.selectbox(
    "Selecione um pedido pra ver o histórico",
    ["(nenhum)"] + list(order_options.keys()),
)

if chosen != "(nenhum)":
    order_id = order_options[chosen]
    selected_order = next((o for o in orders if o["id"] == order_id), None)
    status = selected_order["status"] if selected_order else ""

    # --- Ações disponíveis por status ---
    st.markdown("**Ações**")
    action_cols = st.columns(4)
    terminal_states = {"CONCLUDED", "CANCELLED"}

    def _do_action(path: str, params: dict | None = None) -> None:
        try:
            result = api_post(path, params=params)
            st.success(result.get("message", "Ação enviada."))
            st.cache_data.clear()
        except Exception as exc:
            st.error(f"Falha: {exc}")

    if status == "PLACED":
        if action_cols[0].button("✓ Confirmar", use_container_width=True):
            _do_action(f"/orders/{order_id}/confirm")
        if action_cols[1].button("📦 Pronto pra retirada", use_container_width=True):
            _do_action(f"/orders/{order_id}/ready-to-pickup")
    if status in ("PLACED", "CONFIRMED", "READY_FOR_PICKUP"):
        if action_cols[2].button("🚴 Despachar", use_container_width=True):
            _do_action(f"/orders/{order_id}/dispatch")
    if status not in terminal_states:
        if action_cols[3].button("✗ Cancelar", use_container_width=True, type="secondary"):
            st.session_state["_cancel_target"] = order_id
    if status in terminal_states:
        st.caption(f"Pedido em estado terminal ({status}). Sem ações disponíveis.")

    # --- Form de cancelamento (aparece quando user clica Cancelar) ---
    if st.session_state.get("_cancel_target") == order_id:
        with st.form(f"cancel_form_{order_id}"):
            st.warning("Solicitar cancelamento ao iFood")
            reason = st.text_input(
                "Motivo (obrigatório, mín 3 chars)", value="Problema na loja"
            )
            code = st.selectbox(
                "Código",
                [
                    "501 — Problemas no sistema",
                    "502 — Pedido em duplicidade",
                    "503 — Item indisponível",
                    "504 — Sem motoboy",
                ],
            )
            col_ok, col_cancel = st.columns(2)
            confirmar = col_ok.form_submit_button("Confirmar cancelamento")
            voltar = col_cancel.form_submit_button("Voltar")
            if voltar:
                st.session_state.pop("_cancel_target", None)
                st.rerun()
            if confirmar:
                code_value = code.split(" ")[0]
                _do_action(
                    f"/orders/{order_id}/cancel",
                    params={"reason": reason, "code": code_value},
                )
                st.session_state.pop("_cancel_target", None)

    st.divider()

    # --- Timeline ---
    try:
        events = api_get(f"/orders/{order_id}/events")
    except Exception as e:
        st.error(f"Erro ao buscar eventos: {e}")
        events = []

    if not events:
        st.info("Nenhum evento registrado pra esse pedido.")
    else:
        df_events = pd.DataFrame(events)
        df_events = df_events[["received_at", "code", "full_code", "acknowledged_at"]].rename(
            columns={
                "received_at": "Recebido",
                "code": "Code",
                "full_code": "Status",
                "acknowledged_at": "Confirmado ao iFood",
            }
        )
        st.dataframe(df_events, use_container_width=True, hide_index=True)
