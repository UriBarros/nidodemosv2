"""CSS custom — pinta sidebar de vermelho sem afetar resto da UI."""

from __future__ import annotations

import streamlit as st

_SIDEBAR_CSS = """
<style>
/* Sidebar vermelho */
[data-testid="stSidebar"] {
    background-color: #dc2626;
}

/* Texto e links da sidebar em branco/claro */
[data-testid="stSidebar"] * {
    color: #ffffff !important;
}

/* Inputs/selects da sidebar com fundo branco e texto escuro pra legibilidade */
[data-testid="stSidebar"] input,
[data-testid="stSidebar"] select,
[data-testid="stSidebar"] textarea,
[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background-color: #ffffff !important;
    color: #1f2937 !important;
}

[data-testid="stSidebar"] input::placeholder {
    color: #6b7280 !important;
}

/* Botão "Sair" e similares: borda branca, fundo translúcido */
[data-testid="stSidebar"] button {
    background-color: rgba(255, 255, 255, 0.15) !important;
    border: 1px solid rgba(255, 255, 255, 0.6) !important;
}

[data-testid="stSidebar"] button:hover {
    background-color: rgba(255, 255, 255, 0.25) !important;
}
</style>
"""


def apply_theme() -> None:
    """Injeta CSS custom. Chamar UMA vez por página, após st.set_page_config."""
    st.markdown(_SIDEBAR_CSS, unsafe_allow_html=True)
