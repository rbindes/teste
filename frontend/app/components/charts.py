import plotly.express as px
import plotly.graph_objects as go
import pandas as pd


def expense_pie_chart(expense_items: list[dict]) -> go.Figure:
    df = pd.DataFrame(expense_items)
    fig = px.pie(
        df, values="amount", names="category",
        color_discrete_sequence=px.colors.qualitative.Set3,
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(showlegend=True, margin=dict(t=20, b=20, l=20, r=20))
    return fig


def monthly_bar_chart(monthly_data: list[dict]) -> go.Figure:
    df = pd.DataFrame(monthly_data)
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Receitas", x=df["month"], y=df["income"], marker_color="#2ECC71"))
    fig.add_trace(go.Bar(name="Despesas", x=df["month"], y=df["expenses"], marker_color="#E74C3C"))
    fig.add_trace(go.Scatter(name="Saldo", x=df["month"], y=df["balance"],
                             mode="lines+markers", line=dict(color="#3498DB", width=3)))
    fig.update_layout(barmode="group", margin=dict(t=20, b=20))
    return fig


def person_comparison_chart(data: list[dict], person_a_name: str = "Titular A",
                            person_b_name: str = "Titular B") -> go.Figure:
    df = pd.DataFrame(data)
    fig = go.Figure()
    fig.add_trace(go.Bar(name=person_a_name, x=df["category"],
                         y=df["person_a_amount"], marker_color="#3498DB"))
    fig.add_trace(go.Bar(name=person_b_name, x=df["category"],
                         y=df["person_b_amount"], marker_color="#E74C3C"))
    fig.update_layout(barmode="group", margin=dict(t=20, b=20))
    return fig
