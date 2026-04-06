import os
import uuid

import httpx
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="Login - Finanças Familiar", page_icon="🔐")
st.title("🔐 Login / Registro")

tab_login, tab_register = st.tabs(["Entrar", "Criar Conta"])

with tab_login:
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Entrar")

        if submitted and email and password:
            try:
                with httpx.Client(base_url=BACKEND_URL, timeout=10) as client:
                    resp = client.post("/api/auth/login", json={"email": email, "password": password})
                if resp.status_code == 200:
                    data = resp.json()
                    st.session_state["token"] = data["access_token"]
                    st.session_state["user_name"] = data["user"]["name"]
                    st.session_state["user_id"] = data["user"]["id"]
                    st.session_state["household_id"] = data["user"]["household_id"]
                    st.success("Login realizado!")
                    st.switch_page("pages/1_dashboard.py")
                else:
                    st.error(resp.json().get("detail", "Erro no login"))
            except httpx.ConnectError:
                st.error("Não foi possível conectar ao servidor. Verifique se o backend está rodando.")

with tab_register:
    st.markdown("""
    **Como funciona o cadastro:**
    - O primeiro usuário cria um novo "grupo familiar"
    - O segundo usuário (cônjuge) informa o **ID do grupo** para compartilhar os dados
    """)

    with st.form("register_form"):
        name = st.text_input("Nome")
        email_reg = st.text_input("Email")
        password_reg = st.text_input("Senha", type="password")
        household_input = st.text_input(
            "ID do Grupo Familiar (deixe vazio para criar novo)",
            help="Se seu cônjuge já criou uma conta, peça o ID do grupo a ele(a).",
        )
        submitted_reg = st.form_submit_button("Criar Conta")

        if submitted_reg and name and email_reg and password_reg:
            payload = {
                "name": name,
                "email": email_reg,
                "password": password_reg,
            }
            if household_input:
                payload["household_id"] = household_input

            try:
                with httpx.Client(base_url=BACKEND_URL, timeout=10) as client:
                    resp = client.post("/api/auth/register", json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    st.session_state["token"] = data["access_token"]
                    st.session_state["user_name"] = data["user"]["name"]
                    st.session_state["user_id"] = data["user"]["id"]
                    st.session_state["household_id"] = data["user"]["household_id"]
                    st.success(f"Conta criada! Seu ID do Grupo Familiar: **{data['user']['household_id']}**")
                    st.info("Compartilhe este ID com seu cônjuge para que ele(a) possa acessar os mesmos dados.")
                else:
                    st.error(resp.json().get("detail", "Erro no registro"))
            except httpx.ConnectError:
                st.error("Não foi possível conectar ao servidor.")
