import os

import httpx
import pandas as pd
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="Contas - Finanças Familiar", page_icon="🏦")

if "token" not in st.session_state:
    st.warning("Faça login primeiro.")
    st.switch_page("pages/0_login.py")
    st.stop()

headers = {"Authorization": f"Bearer {st.session_state.token}"}


def api_get(path):
    with httpx.Client(base_url=BACKEND_URL, headers=headers, timeout=30) as c:
        return c.get(path).json()


def api_post(path, json_data):
    with httpx.Client(base_url=BACKEND_URL, headers=headers, timeout=30) as c:
        return c.post(path, json=json_data)


def api_delete(path):
    with httpx.Client(base_url=BACKEND_URL, headers=headers, timeout=30) as c:
        return c.delete(path)


st.title("🏦 Contas Bancárias")
st.markdown("Cadastre as contas e cartões de crédito do casal.")

# Current accounts
accounts = api_get("/api/accounts")

if accounts:
    st.markdown("### Contas cadastradas")
    df = pd.DataFrame(accounts)
    type_labels = {"CHECKING": "Conta Corrente", "SAVINGS": "Poupança", "CREDIT_CARD": "Cartão de Crédito"}
    df["type_label"] = df["type"].map(type_labels)
    display_df = df[["name", "bank_name", "type_label", "last_four_digits"]].copy()
    display_df.columns = ["Nome", "Banco", "Tipo", "Últimos 4 dígitos"]
    st.dataframe(display_df, hide_index=True, use_container_width=True)

    # Delete
    with st.expander("Remover conta"):
        del_options = {a["name"]: a["id"] for a in accounts}
        selected_del = st.selectbox("Conta para remover", list(del_options.keys()))
        if st.button("Remover", type="secondary"):
            resp = api_delete(f"/api/accounts/{del_options[selected_del]}")
            if resp.status_code == 200:
                st.success("Conta removida!")
                st.rerun()
            else:
                st.error("Erro ao remover")

st.markdown("---")
st.markdown("### Adicionar nova conta")

BANKS = [
    "Banco do Brasil",
    "Nubank",
    "Bradesco",
    "Santander",
    "Mercado Pago",
    "Itaú",
    "Caixa Econômica",
    "Inter",
    "C6 Bank",
    "Outro",
]

ACCOUNT_TYPES = {
    "Conta Corrente": "CHECKING",
    "Poupança": "SAVINGS",
    "Cartão de Crédito": "CREDIT_CARD",
}

with st.form("add_account"):
    col1, col2 = st.columns(2)

    bank_name = col1.selectbox("Banco", BANKS)
    account_type = col2.selectbox("Tipo", list(ACCOUNT_TYPES.keys()))

    col3, col4 = st.columns(2)
    # Build default name suggestion
    type_short = "CC" if account_type == "Conta Corrente" else ("Poup" if account_type == "Poupança" else "Cartão")
    user_name = st.session_state.get("user_name", "")
    default_name = f"{bank_name} {type_short} - {user_name}"

    name = col3.text_input("Apelido da conta", value=default_name)
    last_four = col4.text_input("Últimos 4 dígitos (opcional)", max_chars=4)

    owner_id = st.session_state.get("user_id", "")
    st.info(f"Titular: **{user_name}** (para cadastrar conta do cônjuge, peça para ele(a) fazer login)")

    submitted = st.form_submit_button("Adicionar conta", type="primary")

    if submitted and name and bank_name:
        resp = api_post("/api/accounts", {
            "bank_name": bank_name,
            "type": ACCOUNT_TYPES[account_type],
            "name": name,
            "owner_id": owner_id,
            "last_four_digits": last_four or None,
        })
        if resp.status_code == 200:
            st.success(f"Conta '{name}' adicionada!")
            st.rerun()
        else:
            st.error(resp.json().get("detail", "Erro ao criar conta"))

# Show household info
st.markdown("---")
st.info(f"**ID do Grupo Familiar:** `{st.session_state.get('household_id', 'N/A')}`\n\n"
        "Compartilhe com seu cônjuge para que ele(a) acesse os mesmos dados.")
