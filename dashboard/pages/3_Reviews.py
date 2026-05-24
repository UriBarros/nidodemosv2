"""Página de reviews."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from dashboard.lib import api_get, api_post, check_api_health, merchant_selector  # noqa: E402

st.set_page_config(page_title="Reviews | gtrifood", page_icon="⭐", layout="wide")
st.title("Reviews")

if not check_api_health():
    st.stop()

# --- Filtros ---
with st.sidebar:
    st.header("Filtros")
    sel = merchant_selector()
    merchant_id = sel[0] if sel else None

    min_score = st.slider("Score mínimo", min_value=1, max_value=5, value=1)
    answered_filter = st.selectbox("Respondidas", ["(todas)", "Sim", "Não"])
    answered_param: bool | None = None
    if answered_filter == "Sim":
        answered_param = True
    elif answered_filter == "Não":
        answered_param = False

    if st.button("🔄 Sincronizar reviews", use_container_width=True):
        if not merchant_id:
            st.warning("Selecione um merchant primeiro.")
        else:
            with st.spinner("Sincronizando..."):
                try:
                    result = api_post(
                        "/reviews/sync", params={"merchant_id": merchant_id}
                    )
                    st.success(result["message"])
                    st.cache_data.clear()
                except Exception as e:
                    st.error(f"Erro: {e}")

# --- Resumo ---
summary_params: dict = {}
if merchant_id:
    summary_params["merchant_id"] = merchant_id

try:
    summary = api_get("/reviews/summary", params=summary_params)
except Exception as e:
    st.error(f"Erro: {e}")
    st.stop()

col1, col2, col3 = st.columns(3)
col1.metric("Total de reviews", summary["total"])
col2.metric("Média de score", summary["average_score"])
col3.metric("Respondidas", f"{summary['answered_pct']}%")

st.divider()

# --- Lista ---
list_params: dict = {"limit": 200, "min_score": min_score}
if merchant_id:
    list_params["merchant_id"] = merchant_id
if answered_param is not None:
    list_params["answered"] = answered_param

try:
    reviews = api_get("/reviews", params=list_params)
except Exception as e:
    st.error(f"Erro: {e}")
    st.stop()

if not reviews:
    st.info("Nenhum review com esses filtros. Use 'Sincronizar reviews'.")
    st.stop()

df = pd.DataFrame(reviews)
display_cols = [
    "score",
    "customer_name",
    "comment",
    "answered",
    "answer_text",
    "created_at_ifood",
]
df_display = df[display_cols].rename(
    columns={
        "score": "★",
        "customer_name": "Cliente",
        "comment": "Comentário",
        "answered": "Respondida",
        "answer_text": "Resposta",
        "created_at_ifood": "Criado",
    }
)
st.dataframe(df_display, use_container_width=True, hide_index=True)
