import os
from datetime import date, timedelta

import httpx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="Dashboard - Finanças Familiar", page_icon="📊", layout="wide")

if "token" not in st.session_state:
    st.warning("Faça login primeiro.")
    st.switch_page("pages/0_login.py")
    st.stop()


def api_get(path: str, params: dict = None):
    with httpx.Client(
        base_url=BACKEND_URL,
        headers={"Authorization": f"Bearer {st.session_state.token}"},
        timeout=30,
    ) as client:
        resp = client.get(path, params=params)
    if resp.status_code == 401:
        st.session_state.pop("token", None)
        st.switch_page("pages/0_login.py")
    return resp.json()


st.title("📊 Dashboard Financeiro")

# --- Sidebar Filters ---
st.sidebar.header("Filtros")

period = st.sidebar.selectbox("Período", [
    "Mês atual",
    "Último mês",
    "Últimos 3 meses",
    "Últimos 6 meses",
    "Últimos 12 meses",
    "Personalizado",
])

today = date.today()
if period == "Mês atual":
    start_date = today.replace(day=1)
    end_date = today
elif period == "Último mês":
    first_this_month = today.replace(day=1)
    end_date = first_this_month - timedelta(days=1)
    start_date = end_date.replace(day=1)
elif period == "Últimos 3 meses":
    start_date = today - timedelta(days=90)
    end_date = today
elif period == "Últimos 6 meses":
    start_date = today - timedelta(days=180)
    end_date = today
elif period == "Últimos 12 meses":
    start_date = today - timedelta(days=365)
    end_date = today
else:
    col1, col2 = st.sidebar.columns(2)
    start_date = col1.date_input("De", today.replace(day=1))
    end_date = col2.date_input("Até", today)

# Fetch members for person filter
members = api_get("/api/accounts")
owner_ids = list({a["owner_id"] for a in members})
owner_names = {}
for a in members:
    if a["owner_id"] not in owner_names:
        owner_names[a["owner_id"]] = a["name"].split(" - ")[-1] if " - " in a["name"] else a["owner_id"][:8]

person_filter = st.sidebar.radio(
    "Titular",
    ["Casal (todos)"] + [f"{owner_names.get(oid, oid[:8])}" for oid in owner_ids],
)
owner_id = None
if person_filter != "Casal (todos)" and owner_ids:
    idx = [owner_names.get(oid, oid[:8]) for oid in owner_ids].index(person_filter)
    owner_id = owner_ids[idx]

params = {
    "start_date": str(start_date),
    "end_date": str(end_date),
}
if owner_id:
    params["owner_id"] = owner_id

# --- DRE ---
dre = api_get("/api/dashboard/dre", params)

st.markdown(f"### DRE - {dre['period']}")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Receitas", f"R$ {dre['total_income']:,.2f}")
col2.metric("Despesas", f"R$ {dre['total_expenses']:,.2f}")
col3.metric("Saldo", f"R$ {dre['balance']:,.2f}",
            delta=f"{dre['savings_rate']:.1f}% poupança")
col4.metric("Taxa Poupança", f"{dre['savings_rate']:.1f}%")

# DRE Table
st.markdown("---")
col_left, col_right = st.columns(2)

with col_left:
    st.markdown("#### (+) Receitas")
    if dre["income_items"]:
        df_income = pd.DataFrame(dre["income_items"])
        df_income["amount"] = df_income["amount"].apply(lambda x: f"R$ {x:,.2f}")
        df_income["percentage"] = df_income["percentage"].apply(lambda x: f"{x:.1f}%")
        df_income.columns = ["Categoria", "Valor", "%"]
        st.dataframe(df_income, hide_index=True, use_container_width=True)
    else:
        st.info("Nenhuma receita no período")

with col_right:
    st.markdown("#### (-) Despesas")
    if dre["expense_items"]:
        df_expenses = pd.DataFrame(dre["expense_items"])
        df_expenses["amount"] = df_expenses["amount"].apply(lambda x: f"R$ {x:,.2f}")
        df_expenses["percentage"] = df_expenses["percentage"].apply(lambda x: f"{x:.1f}%")
        df_expenses.columns = ["Categoria", "Valor", "%"]
        st.dataframe(df_expenses, hide_index=True, use_container_width=True)
    else:
        st.info("Nenhuma despesa no período")

# --- Charts ---
st.markdown("---")
st.markdown("### Gráficos")

tab_pie, tab_monthly, tab_person = st.tabs(["Por Categoria", "Evolução Mensal", "Por Pessoa"])

with tab_pie:
    if dre["expense_items"]:
        df_pie = pd.DataFrame(dre["expense_items"])
        fig = px.pie(
            df_pie, values="amount", names="category",
            title="Distribuição de Gastos por Categoria",
            color_discrete_sequence=px.colors.qualitative.Set3,
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig, use_container_width=True)

with tab_monthly:
    monthly_params = {"months": 12}
    if owner_id:
        monthly_params["owner_id"] = owner_id
    monthly = api_get("/api/dashboard/monthly", monthly_params)
    if monthly:
        df_monthly = pd.DataFrame(monthly)
        fig = go.Figure()
        fig.add_trace(go.Bar(name="Receitas", x=df_monthly["month"], y=df_monthly["income"],
                             marker_color="#2ECC71"))
        fig.add_trace(go.Bar(name="Despesas", x=df_monthly["month"], y=df_monthly["expenses"],
                             marker_color="#E74C3C"))
        fig.add_trace(go.Scatter(name="Saldo", x=df_monthly["month"], y=df_monthly["balance"],
                                 mode="lines+markers", line=dict(color="#3498DB", width=3)))
        fig.update_layout(title="Evolução Mensal", barmode="group", xaxis_title="Mês", yaxis_title="R$")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem dados mensais")

with tab_person:
    by_person = api_get("/api/dashboard/by-person", {
        "start_date": str(start_date),
        "end_date": str(end_date),
    })
    if by_person:
        df_person = pd.DataFrame(by_person)
        fig = go.Figure()
        fig.add_trace(go.Bar(name="Titular A", x=df_person["category"],
                             y=df_person["person_a_amount"], marker_color="#3498DB"))
        fig.add_trace(go.Bar(name="Titular B", x=df_person["category"],
                             y=df_person["person_b_amount"], marker_color="#E74C3C"))
        fig.update_layout(title="Gastos por Pessoa e Categoria", barmode="group",
                          xaxis_title="Categoria", yaxis_title="R$")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Cadastre contas para ambos os titulares para ver a comparação")

# --- Top Expenses ---
st.markdown("---")
st.markdown("### Top 10 Maiores Gastos")
top = api_get("/api/dashboard/top-expenses", params)
if top:
    df_top = pd.DataFrame(top)
    df_top["amount"] = df_top["amount"].apply(lambda x: f"R$ {x:,.2f}")
    df_top.columns = ["Data", "Descrição", "Valor", "Categoria", "Conta"]
    st.dataframe(df_top, hide_index=True, use_container_width=True)
else:
    st.info("Sem dados no período")
