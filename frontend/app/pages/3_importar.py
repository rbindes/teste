import os

import httpx
import pandas as pd
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="Importar - Finanças Familiar", page_icon="📤")

if "token" not in st.session_state:
    st.warning("Faça login primeiro.")
    st.switch_page("pages/0_login.py")
    st.stop()

headers = {"Authorization": f"Bearer {st.session_state.token}"}


def api_get(path, params=None):
    with httpx.Client(base_url=BACKEND_URL, headers=headers, timeout=30) as c:
        return c.get(path, params=params).json()


st.title("📤 Importar Extratos")

st.markdown("""
**Formatos suportados:** OFX, CSV, PDF, Imagem (JPG/PNG)

**Como exportar do seu banco:**
| Banco | Formato | Onde encontrar |
|-------|---------|---------------|
| Banco do Brasil | OFX | Internet Banking > Extrato > Download > Money 2000+ |
| Nubank | CSV/OFX | App > Conta > Solicitar extrato > Exportar |
| Bradesco | OFX | Internet Banking > Saldos e Extratos > Salvar como arquivo |
| Santander | OFX | Internet Banking > Extrato > Exportar |
| Mercado Pago | PDF | App > Atividade > Baixar extrato |
""")

st.markdown("---")

# Fetch accounts
accounts = api_get("/api/accounts")

if not accounts:
    st.warning("Cadastre pelo menos uma conta bancária primeiro na página 'Contas'.")
    st.stop()

account_options = {a["name"]: a["id"] for a in accounts}

# Upload form
selected_account = st.selectbox("Conta destino", list(account_options.keys()))
uploaded_file = st.file_uploader(
    "Arquivo do extrato",
    type=["ofx", "qfx", "csv", "pdf", "jpg", "jpeg", "png"],
    help="Arraste ou selecione o arquivo exportado do banco",
)

if uploaded_file:
    if st.button("Processar arquivo", type="primary"):
        account_id = account_options[selected_account]

        with httpx.Client(base_url=BACKEND_URL, headers=headers, timeout=60) as client:
            resp = client.post(
                "/api/imports/upload",
                files={"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)},
                data={"account_id": str(account_id)},
            )

        if resp.status_code != 200:
            st.error(resp.json().get("detail", "Erro ao processar arquivo"))
            st.stop()

        preview = resp.json()
        st.session_state["upload_preview"] = preview
        st.success(f"**{preview['total_count']}** transações encontradas!")

# Show preview
if "upload_preview" in st.session_state:
    preview = st.session_state["upload_preview"]
    st.markdown(f"### Preview - {preview['filename']} ({preview['file_type']})")

    df = pd.DataFrame(preview["transactions"])
    df["amount_display"] = df["amount"].apply(lambda x: f"R$ {x:,.2f}")
    display_df = df[["date", "description", "amount_display", "type"]].copy()
    display_df.columns = ["Data", "Descrição", "Valor", "Tipo"]
    st.dataframe(display_df, hide_index=True, use_container_width=True)

    # Summary
    total_income = sum(t["amount"] for t in preview["transactions"] if t["type"] == "INCOME")
    total_expense = sum(abs(t["amount"]) for t in preview["transactions"] if t["type"] == "EXPENSE")

    col1, col2, col3 = st.columns(3)
    col1.metric("Receitas", f"R$ {total_income:,.2f}")
    col2.metric("Despesas", f"R$ {total_expense:,.2f}")
    col3.metric("Total", f"{preview['total_count']} transações")

    col_confirm, col_cancel = st.columns(2)

    with col_confirm:
        if st.button("Confirmar importação", type="primary"):
            with httpx.Client(base_url=BACKEND_URL, headers=headers, timeout=30) as client:
                resp = client.post(f"/api/imports/{preview['upload_id']}/confirm")

            if resp.status_code == 200:
                result = resp.json()
                st.success(
                    f"Importação concluída! "
                    f"**{result['transactions_imported']}** importadas, "
                    f"**{result['transactions_skipped']}** duplicatas ignoradas."
                )
                st.session_state.pop("upload_preview", None)
                st.rerun()
            else:
                st.error(resp.json().get("detail", "Erro na importação"))

    with col_cancel:
        if st.button("Cancelar"):
            st.session_state.pop("upload_preview", None)
            st.rerun()

# History
st.markdown("---")
st.markdown("### Histórico de Importações")
history = api_get("/api/imports/history")
if history:
    df_hist = pd.DataFrame(history)
    df_hist = df_hist[["created_at", "filename", "file_type", "account_name", "transactions_imported", "transactions_skipped"]]
    df_hist.columns = ["Data", "Arquivo", "Tipo", "Conta", "Importadas", "Duplicatas"]
    st.dataframe(df_hist, hide_index=True, use_container_width=True)
else:
    st.info("Nenhuma importação realizada ainda.")
