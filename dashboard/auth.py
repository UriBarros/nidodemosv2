"""Helpers de autenticação Supabase pro dashboard Streamlit.

Usa supabase-py. Sessão persistida em st.session_state pra sobreviver entre
reruns do Streamlit (não entre sessões do navegador).
"""

from __future__ import annotations

import os
from typing import Any

import streamlit as st
from supabase import Client, create_client


@st.cache_resource
def _client() -> Client:
    url = os.getenv("SUPABASE_URL") or ""
    key = os.getenv("SUPABASE_ANON_KEY") or ""
    if not url or not key:
        st.error(
            "SUPABASE_URL e SUPABASE_ANON_KEY precisam estar no .env "
            "(ou exportados como env var) pra dashboard funcionar."
        )
        st.stop()
    return create_client(url, key)


def sign_in(email: str, password: str) -> dict[str, Any] | None:
    """Login. Grava session em st.session_state. Retorna dict ou None se falhar."""
    try:
        response = _client().auth.sign_in_with_password({"email": email, "password": password})
    except Exception as e:
        st.error(f"Falha no login: {e}")
        return None

    if not response.session:
        st.error("Login falhou: sem sessão retornada")
        return None

    st.session_state["access_token"] = response.session.access_token
    st.session_state["refresh_token"] = response.session.refresh_token
    st.session_state["user_email"] = response.user.email if response.user else email
    return {"email": st.session_state["user_email"]}


def sign_up(email: str, password: str) -> bool:
    """Cadastro. Retorna True se ok."""
    try:
        response = _client().auth.sign_up({"email": email, "password": password})
    except Exception as e:
        st.error(f"Falha no cadastro: {e}")
        return False

    if not response.user:
        st.error("Cadastro falhou")
        return False

    # Se o projeto tiver confirm email desabilitado, já vem session
    if response.session:
        st.session_state["access_token"] = response.session.access_token
        st.session_state["refresh_token"] = response.session.refresh_token
        st.session_state["user_email"] = response.user.email or email
        return True

    st.info(
        "Conta criada. Verifique seu email pra confirmar (se confirmação "
        "estiver ativa no Supabase). Depois faça login."
    )
    return True


def sign_out() -> None:
    """Limpa sessão local + revoga token no Supabase."""
    try:
        _client().auth.sign_out()
    except Exception:
        pass
    for key in ("access_token", "refresh_token", "user_email"):
        st.session_state.pop(key, None)


def get_access_token() -> str | None:
    return st.session_state.get("access_token")


def is_authenticated() -> bool:
    return "access_token" in st.session_state


def require_auth() -> None:
    """Bloqueia a página se usuário não estiver autenticado."""
    if not is_authenticated():
        st.warning("🔒 Faça login na página inicial pra acessar.")
        st.stop()


def render_login_form() -> None:
    """Form de login + cadastro. Chama em app.py quando não autenticado."""
    st.subheader("Acesso")
    tab_login, tab_signup = st.tabs(["Entrar", "Criar conta"])

    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Senha", type="password", key="login_pw")
            submitted = st.form_submit_button("Entrar", use_container_width=True)
            if submitted:
                result = sign_in(email, password)
                if result:
                    st.success(f"Logado como {result['email']}")
                    st.rerun()

    with tab_signup:
        with st.form("signup_form"):
            email_s = st.text_input("Email", key="signup_email")
            password_s = st.text_input(
                "Senha (mín 6 caracteres)", type="password", key="signup_pw"
            )
            submitted_s = st.form_submit_button("Criar conta", use_container_width=True)
            if submitted_s:
                if sign_up(email_s, password_s):
                    st.rerun()


def render_sidebar_user() -> None:
    """Mostra info do user logado + botão de logout na sidebar."""
    if is_authenticated():
        with st.sidebar:
            st.divider()
            st.caption(f"👤 {st.session_state.get('user_email', '?')}")
            if st.button("Sair", use_container_width=True):
                sign_out()
                st.rerun()
