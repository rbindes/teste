import os

import httpx
import pandas as pd
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="Categorias - Finanças Familiar", page_icon="🏷️")

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


st.title("🏷️ Categorias e Regras")

# List categories
categories = api_get("/api/transactions/categories")

st.markdown("### Categorias disponíveis")
if categories:
    df = pd.DataFrame(categories)
    df_display = df[["icon", "name", "color"]].copy()
    df_display.columns = ["Ícone", "Nome", "Cor"]
    st.dataframe(df_display, hide_index=True, use_container_width=True)

# Add rule
st.markdown("---")
st.markdown("### Adicionar Regra de Categorização")
st.markdown("""
Regras permitem categorizar transações automaticamente.
Se a **descrição** de uma transação contém o **padrão**, ela será categorizada automaticamente.

**Exemplo:** Padrão `ifood` → Categoria `Alimentação` (qualquer transação com "ifood" no nome será categorizada como Alimentação)
""")

with st.form("add_rule"):
    pattern = st.text_input("Padrão (texto que aparece na descrição)", placeholder="ex: ifood, uber, netflix")
    category_name = st.selectbox("Categoria", [c["name"] for c in categories])
    priority = st.slider("Prioridade (maior = mais importante)", 0, 300, 200)
    submitted = st.form_submit_button("Criar Regra", type="primary")

    if submitted and pattern:
        cat_id = next(c["id"] for c in categories if c["name"] == category_name)
        resp = api_post("/api/transactions/categories/rules", {
            "pattern": pattern,
            "category_id": cat_id,
            "priority": priority,
        })
        if resp.status_code == 200:
            st.success(f"Regra criada: '{pattern}' → {category_name}")
        else:
            st.error("Erro ao criar regra")
