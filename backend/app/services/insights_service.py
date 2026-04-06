import json
import uuid
from datetime import date, timedelta

from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction
from app.schemas.models import InsightItem


async def _get_period_data(
    db: AsyncSession, household_id: uuid.UUID, start: date, end: date
) -> dict:
    query = (
        select(
            Category.name.label("cat_name"),
            Transaction.type,
            func.sum(Transaction.amount).label("total"),
            func.count(Transaction.id).label("count"),
        )
        .outerjoin(Category, Transaction.category_id == Category.id)
        .join(Account, Transaction.account_id == Account.id)
        .where(
            Account.household_id == household_id,
            Transaction.date >= start,
            Transaction.date <= end,
        )
        .group_by(Category.name, Transaction.type)
    )
    result = await db.execute(query)
    rows = result.all()

    income = {}
    expenses = {}
    total_income = 0.0
    total_expenses = 0.0

    for cat_name, tx_type, total, count in rows:
        cat_name = cat_name or "Sem categoria"
        val = float(total or 0)
        if tx_type == "INCOME":
            income[cat_name] = val
            total_income += val
        else:
            expenses[cat_name] = abs(val)
            total_expenses += abs(val)

    return {
        "period": f"{start} a {end}",
        "total_income": total_income,
        "total_expenses": total_expenses,
        "balance": total_income - total_expenses,
        "income_by_category": income,
        "expenses_by_category": expenses,
    }


def _build_prompt(current: dict, previous: dict) -> str:
    return f"""Você é um consultor financeiro pessoal analisando as finanças de um casal brasileiro.

DADOS DO PERÍODO ATUAL ({current['period']}):
- Receita total: R$ {current['total_income']:,.2f}
- Despesa total: R$ {current['total_expenses']:,.2f}
- Saldo: R$ {current['balance']:,.2f}
- Receitas por categoria: {json.dumps(current['income_by_category'], ensure_ascii=False)}
- Despesas por categoria: {json.dumps(current['expenses_by_category'], ensure_ascii=False)}

DADOS DO PERÍODO ANTERIOR ({previous['period']}):
- Receita total: R$ {previous['total_income']:,.2f}
- Despesa total: R$ {previous['total_expenses']:,.2f}
- Saldo: R$ {previous['balance']:,.2f}
- Despesas por categoria: {json.dumps(previous['expenses_by_category'], ensure_ascii=False)}

Gere exatamente 5 insights em JSON. Cada insight deve ter:
- "type": "ALERT" | "OPPORTUNITY" | "GOAL" | "COMPARISON"
- "title": título curto (max 60 chars)
- "description": explicação detalhada com valores em R$ (max 200 chars)
- "icon": emoji relevante

Responda APENAS com o array JSON, sem markdown nem explicação adicional.
Foque em:
1. Categorias com maior variação vs período anterior
2. Oportunidades de economia
3. Projeção de poupança anual
4. Proporção de gastos fixos vs variáveis
5. Saúde financeira geral (% da renda comprometida)"""


async def generate_insights(
    db: AsyncSession,
    household_id: uuid.UUID,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[InsightItem]:
    if not settings.ANTHROPIC_API_KEY:
        return [
            InsightItem(
                type="ALERT",
                title="API Key não configurada",
                description="Configure ANTHROPIC_API_KEY no .env para gerar insights com IA.",
                icon="⚠️",
            )
        ]

    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date.replace(day=1)

    # Previous period (same duration)
    duration = (end_date - start_date).days
    prev_end = start_date - timedelta(days=1)
    prev_start = prev_end - timedelta(days=duration)

    current_data = await _get_period_data(db, household_id, start_date, end_date)
    previous_data = await _get_period_data(db, household_id, prev_start, prev_end)

    if current_data["total_income"] == 0 and current_data["total_expenses"] == 0:
        return [
            InsightItem(
                type="ALERT",
                title="Sem dados no período",
                description="Importe extratos bancários para gerar insights financeiros.",
                icon="📊",
            )
        ]

    import anthropic

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    prompt = _build_prompt(current_data, previous_data)

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    try:
        content = response.content[0].text
        # Clean up potential markdown wrapping
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            content = content.rsplit("```", 1)[0]
        insights_data = json.loads(content)
        return [InsightItem(**item) for item in insights_data]
    except (json.JSONDecodeError, IndexError, KeyError):
        return [
            InsightItem(
                type="ALERT",
                title="Erro ao processar insights",
                description="Não foi possível interpretar a resposta da IA. Tente novamente.",
                icon="❌",
            )
        ]
