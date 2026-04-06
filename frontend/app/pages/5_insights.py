import os
from datetime import date, timedelta

import httpx
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="Insights - Finanças Familiar", page_icon="💡")

if "token" not in st.session_state:
    st.warning("Faça login primeiro.")
    st.switch_page("pages/0_login.py")
    st.stop()

headers = {"Authorization": f"Bearer {st.session_state.token}"}

st.title("💡 Insights Financeiros")
st.markdown("Análise inteligente das suas finanças usando IA.")

# Period selector
col1, col2 = st.columns(2)
start_date = col1.date_input("De", date.today().replace(day=1))
end_date = col2.date_input("Até", date.today())

if st.button("Gerar Insights", type="primary"):
    with st.spinner("Analisando suas finanças com IA..."):
        with httpx.Client(base_url=BACKEND_URL, headers=headers, timeout=60) as client:
            resp = client.get("/api/dashboard/insights", params={
                "start_date": str(start_date),
                "end_date": str(end_date),
            })

        if resp.status_code == 200:
            insights = resp.json()
            st.session_state["insights"] = insights
        else:
            st.error("Erro ao gerar insights")

if "insights" in st.session_state:
    insights = st.session_state["insights"]

    type_colors = {
        "ALERT": "🔴",
        "OPPORTUNITY": "🟢",
        "GOAL": "🔵",
        "COMPARISON": "🟡",
    }
    type_labels = {
        "ALERT": "Alerta",
        "OPPORTUNITY": "Oportunidade",
        "GOAL": "Meta",
        "COMPARISON": "Comparação",
    }

    for insight in insights:
        icon = insight.get("icon", "📊")
        insight_type = insight.get("type", "ALERT")
        color_dot = type_colors.get(insight_type, "⚪")
        label = type_labels.get(insight_type, insight_type)

        with st.container():
            st.markdown(f"""
            {color_dot} **{label}** | {icon} {insight['title']}

            {insight['description']}

            ---
            """)
