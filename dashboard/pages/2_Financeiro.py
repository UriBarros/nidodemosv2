"""Página financeira."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from datetime import date, timedelta  # noqa: E402

import pandas as pd  # noqa: E402
import plotly.express as px  # noqa: E402
import streamlit as st  # noqa: E402

from dashboard.auth import render_sidebar_user, require_auth  # noqa: E402
from dashboard.lib import api_get, api_post, check_api_health, merchant_selector  # noqa: E402

st.set_page_config(page_title="Financeiro | gtrifood", page_icon="💰", layout="wide")
st.title("Financeiro")

if not check_api_health():
    st.stop()

render_sidebar_user()
require_auth()

# --- Filtros ---
with st.sidebar:
    st.header("Filtros")
    sel = merchant_selector()
    merchant_id = sel[0] if sel else None

    end_date = st.date_input("Até", value=date.today())
    begin_date = st.date_input("De", value=end_date - timedelta(days=30))

    if st.button("🔄 Sincronizar financeiro", use_container_width=True):
        if not merchant_id:
            st.warning("Selecione um merchant primeiro.")
        else:
            days = (end_date - begin_date).days or 30
            with st.spinner("Sincronizando..."):
                try:
                    result = api_post(
                        "/financial/sync",
                        params={"merchant_id": merchant_id, "days_back": days},
                    )
                    st.success(result["message"])
                    st.cache_data.clear()
                except Exception as e:
                    st.error(f"Erro: {e}")

# --- Resumo ---
summary_params = {}
if merchant_id:
    summary_params["merchant_id"] = merchant_id

try:
    summary = api_get("/financial/summary", params=summary_params)
except Exception as e:
    st.error(f"Erro: {e}")
    st.stop()

col1, col2, col3 = st.columns(3)
col1.metric("Vendas", f"R$ {summary.get('SALE', 0):,.2f}")
col2.metric("Antecipações", f"R$ {summary.get('ANTICIPATION', 0):,.2f}")
col3.metric("Ocorrências", f"R$ {summary.get('OCCURRENCE', 0):,.2f}")

st.divider()

# --- Lista detalhada ---
list_params: dict = {
    "limit": 500,
    "begin": begin_date.isoformat(),
    "end": end_date.isoformat(),
}
if merchant_id:
    list_params["merchant_id"] = merchant_id

try:
    events = api_get("/financial", params=list_params)
except Exception as e:
    st.error(f"Erro: {e}")
    st.stop()

if not events:
    st.info("Nenhum evento financeiro no período. Use 'Sincronizar financeiro'.")
    st.stop()

df = pd.DataFrame(events)
df["amount"] = df["amount"].astype(float)

# --- Gráfico ---
if "competence_date" in df.columns and df["competence_date"].notna().any():
    chart_df = df.dropna(subset=["competence_date"]).copy()
    chart_df["competence_date"] = pd.to_datetime(chart_df["competence_date"])
    daily = chart_df.groupby(["competence_date", "event_type"])["amount"].sum().reset_index()

    fig = px.bar(
        daily,
        x="competence_date",
        y="amount",
        color="event_type",
        title="Movimentação por dia",
        labels={"amount": "R$", "competence_date": "Data"},
    )
    st.plotly_chart(fig, use_container_width=True)

# --- Tabela ---
st.subheader("Eventos detalhados")
display_cols = ["event_type", "competence_date", "amount", "description", "synced_at"]
df_display = df[display_cols].rename(
    columns={
        "event_type": "Tipo",
        "competence_date": "Data",
        "amount": "Valor (R$)",
        "description": "Descrição",
        "synced_at": "Sincronizado",
    }
)
st.dataframe(df_display, use_container_width=True, hide_index=True)
