import os

import httpx
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Finanças Familiar",
    page_icon="💰",
    layout="wide",
)


def api_client() -> httpx.Client:
    headers = {}
    if "token" in st.session_state:
        headers["Authorization"] = f"Bearer {st.session_state.token}"
    return httpx.Client(base_url=BACKEND_URL, headers=headers, timeout=30.0)


def check_auth():
    if "token" not in st.session_state:
        st.switch_page("pages/0_login.py")


# Store api_client in session for reuse by pages
st.session_state["backend_url"] = BACKEND_URL

if "token" not in st.session_state:
    st.title("💰 Finanças Familiar")
    st.markdown("### Bem-vindo ao seu sistema de controle financeiro!")
    st.markdown("""
    **O que este sistema faz:**
    - Importa extratos bancários (OFX, CSV, PDF, imagem)
    - Categoriza gastos automaticamente
    - Dashboard DRE (Receitas vs Despesas)
    - Filtra por pessoa ou casal
    - Insights financeiros com IA

    **Bancos suportados:**
    Banco do Brasil, Nubank, Bradesco, Santander, Mercado Pago

    ---
    """)
    st.info("👈 Use o menu lateral para fazer login ou criar conta.")
else:
    st.title("💰 Finanças Familiar")
    st.success(f"Logado como **{st.session_state.get('user_name', '')}**")
    st.markdown("""
    ### Menu rápido
    - 📊 **Dashboard** — DRE e gráficos
    - 📋 **Transações** — ver e categorizar
    - 📤 **Importar** — upload de extratos
    - 🏦 **Contas** — gerenciar contas bancárias
    - 💡 **Insights** — análise com IA
    - 🏷️ **Categorias** — regras de categorização
    """)

    if st.button("Sair"):
        for key in ["token", "user_name", "user_id", "household_id"]:
            st.session_state.pop(key, None)
        st.rerun()
