import os
from datetime import date, timedelta

import httpx
import pandas as pd
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="Transações - Finanças Familiar", page_icon="📋", layout="wide")

if "token" not in st.session_state:
    st.warning("Faça login primeiro.")
    st.switch_page("pages/0_login.py")
    st.stop()

headers = {"Authorization": f"Bearer {st.session_state.token}"}


def api_get(path, params=None):
    with httpx.Client(base_url=BACKEND_URL, headers=headers, timeout=30) as c:
        return c.get(path, params=params).json()


def api_patch(path, json_data):
    with httpx.Client(base_url=BACKEND_URL, headers=headers, timeout=30) as c:
        return c.patch(path, json=json_data)


st.title("📋 Transações")

# Filters
col1, col2, col3, col4 = st.columns(4)
start_date = col1.date_input("De", date.today().replace(day=1))
end_date = col2.date_input("Até", date.today())

# Fetch accounts and categories for filters
accounts = api_get("/api/accounts")
categories = api_get("/api/transactions/categories")

account_options = {"Todas": None} | {a["name"]: a["id"] for a in accounts}
category_options = {"Todas": None} | {c["name"]: c["id"] for c in categories}

selected_account = col3.selectbox("Conta", list(account_options.keys()))
selected_category = col4.selectbox("Categoria", list(category_options.keys()))

params = {
    "start_date": str(start_date),
    "end_date": str(end_date),
    "limit": 500,
}
if account_options[selected_account]:
    params["account_id"] = account_options[selected_account]
if category_options[selected_category]:
    params["category_id"] = category_options[selected_category]

transactions = api_get("/api/transactions", params)

if not transactions:
    st.info("Nenhuma transação encontrada. Importe extratos na página 'Importar'.")
    st.stop()

# Summary
total_income = sum(t["amount"] for t in transactions if t["type"] == "INCOME")
total_expense = sum(abs(t["amount"]) for t in transactions if t["type"] == "EXPENSE")

col1, col2, col3 = st.columns(3)
col1.metric("Receitas", f"R$ {total_income:,.2f}")
col2.metric("Despesas", f"R$ {total_expense:,.2f}")
col3.metric("Transações", len(transactions))

st.markdown("---")

# Table
df = pd.DataFrame(transactions)
df["amount_display"] = df["amount"].apply(lambda x: f"R$ {x:,.2f}")
df["category_display"] = df["category_name"].fillna("Sem categoria")

display_df = df[["date", "description", "amount_display", "category_display", "source"]].copy()
display_df.columns = ["Data", "Descrição", "Valor", "Categoria", "Origem"]

st.dataframe(display_df, hide_index=True, use_container_width=True, height=500)

# Recategorize section
st.markdown("---")
st.markdown("### Recategorizar Transação")

with st.form("recategorize"):
    tx_options = {
        f"{t['date']} | {t['description'][:50]} | R$ {t['amount']:.2f}": t["id"]
        for t in transactions
    }
    selected_tx = st.selectbox("Transação", list(tx_options.keys()))
    new_category = st.selectbox("Nova Categoria", [c["name"] for c in categories])
    create_rule = st.checkbox("Criar regra automática para transações similares", value=True)
    submitted = st.form_submit_button("Recategorizar")

    if submitted and selected_tx:
        tx_id = tx_options[selected_tx]
        cat_id = next(c["id"] for c in categories if c["name"] == new_category)
        resp = api_patch(f"/api/transactions/{tx_id}/category", {
            "category_id": cat_id,
            "create_rule": create_rule,
        })
        if resp.status_code == 200:
            st.success(f"Transação recategorizada para '{new_category}'!")
            st.rerun()
        else:
            st.error("Erro ao recategorizar")
