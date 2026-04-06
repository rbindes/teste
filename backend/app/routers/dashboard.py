import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, case, extract
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.user import User
from app.routers.deps import get_current_user
from app.schemas.models import (
    DREResponse,
    DRELineItem,
    MonthlyDataPoint,
    PersonComparisonItem,
    TopExpenseItem,
    InsightItem,
)
from app.services.insights_service import generate_insights

router = APIRouter()


def _default_dates(start_date: date | None, end_date: date | None) -> tuple[date, date]:
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date.replace(day=1)
    return start_date, end_date


@router.get("/dre", response_model=DREResponse)
async def get_dre(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    start_date: date | None = None,
    end_date: date | None = None,
    owner_id: uuid.UUID | None = None,
):
    start_date, end_date = _default_dates(start_date, end_date)

    query = (
        select(
            Category.name,
            Transaction.type,
            func.sum(Transaction.amount).label("total"),
        )
        .outerjoin(Category, Transaction.category_id == Category.id)
        .join(Account, Transaction.account_id == Account.id)
        .where(
            Account.household_id == user.household_id,
            Transaction.date >= start_date,
            Transaction.date <= end_date,
        )
    )

    if owner_id:
        query = query.where(Account.owner_id == owner_id)

    query = query.group_by(Category.name, Transaction.type)
    result = await db.execute(query)
    rows = result.all()

    income_items = []
    expense_items = []
    total_income = 0.0
    total_expenses = 0.0

    for cat_name, tx_type, total in rows:
        total_val = float(total or 0)
        cat_name = cat_name or "Sem categoria"

        if tx_type == "INCOME":
            total_income += total_val
            income_items.append(DRELineItem(category=cat_name, amount=total_val, percentage=0))
        else:
            total_expenses += abs(total_val)
            expense_items.append(DRELineItem(category=cat_name, amount=abs(total_val), percentage=0))

    # Calculate percentages
    for item in income_items:
        item.percentage = (item.amount / total_income * 100) if total_income else 0
    for item in expense_items:
        item.percentage = (item.amount / total_expenses * 100) if total_expenses else 0

    # Sort by amount desc
    income_items.sort(key=lambda x: x.amount, reverse=True)
    expense_items.sort(key=lambda x: x.amount, reverse=True)

    balance = total_income - total_expenses
    savings_rate = (balance / total_income * 100) if total_income else 0

    period_str = f"{start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}"

    return DREResponse(
        period=period_str,
        total_income=total_income,
        income_items=income_items,
        total_expenses=total_expenses,
        expense_items=expense_items,
        balance=balance,
        savings_rate=savings_rate,
    )


@router.get("/monthly", response_model=list[MonthlyDataPoint])
async def get_monthly(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    months: int = Query(default=12, le=24),
    owner_id: uuid.UUID | None = None,
):
    end_date = date.today()
    start_date = end_date - timedelta(days=months * 31)

    query = (
        select(
            extract("year", Transaction.date).label("year"),
            extract("month", Transaction.date).label("month"),
            func.sum(case((Transaction.type == "INCOME", Transaction.amount), else_=0)).label("income"),
            func.sum(case((Transaction.type == "EXPENSE", func.abs(Transaction.amount)), else_=0)).label("expenses"),
        )
        .join(Account, Transaction.account_id == Account.id)
        .where(
            Account.household_id == user.household_id,
            Transaction.date >= start_date,
            Transaction.date <= end_date,
        )
    )

    if owner_id:
        query = query.where(Account.owner_id == owner_id)

    query = query.group_by("year", "month").order_by("year", "month")
    result = await db.execute(query)
    rows = result.all()

    return [
        MonthlyDataPoint(
            month=f"{int(year)}-{int(month):02d}",
            income=float(income or 0),
            expenses=float(expenses or 0),
            balance=float((income or 0)) - float((expenses or 0)),
        )
        for year, month, income, expenses in rows
    ]


@router.get("/by-person", response_model=list[PersonComparisonItem])
async def get_by_person(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    start_date: date | None = None,
    end_date: date | None = None,
):
    start_date, end_date = _default_dates(start_date, end_date)

    # Get household members
    members_result = await db.execute(
        select(User).where(User.household_id == user.household_id)
    )
    members = members_result.scalars().all()
    if len(members) < 2:
        return []

    person_a, person_b = members[0], members[1]

    query = (
        select(
            Category.name.label("cat_name"),
            Account.owner_id,
            func.sum(func.abs(Transaction.amount)).label("total"),
        )
        .outerjoin(Category, Transaction.category_id == Category.id)
        .join(Account, Transaction.account_id == Account.id)
        .where(
            Account.household_id == user.household_id,
            Transaction.type == "EXPENSE",
            Transaction.date >= start_date,
            Transaction.date <= end_date,
        )
        .group_by(Category.name, Account.owner_id)
    )

    result = await db.execute(query)
    rows = result.all()

    # Pivot by category
    data: dict[str, dict[str, float]] = {}
    for cat_name, owner_id, total in rows:
        cat_name = cat_name or "Sem categoria"
        if cat_name not in data:
            data[cat_name] = {"a": 0.0, "b": 0.0}
        key = "a" if owner_id == person_a.id else "b"
        data[cat_name][key] = float(total or 0)

    return [
        PersonComparisonItem(
            category=cat,
            person_a_amount=vals["a"],
            person_b_amount=vals["b"],
        )
        for cat, vals in sorted(data.items(), key=lambda x: x[1]["a"] + x[1]["b"], reverse=True)
    ]


@router.get("/top-expenses", response_model=list[TopExpenseItem])
async def get_top_expenses(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = Query(default=10, le=50),
):
    start_date, end_date = _default_dates(start_date, end_date)

    query = (
        select(Transaction, Category.name.label("cat_name"), Account.name.label("acc_name"))
        .outerjoin(Category, Transaction.category_id == Category.id)
        .join(Account, Transaction.account_id == Account.id)
        .where(
            Account.household_id == user.household_id,
            Transaction.type == "EXPENSE",
            Transaction.date >= start_date,
            Transaction.date <= end_date,
        )
        .order_by(Transaction.amount.asc())  # most negative first
        .limit(limit)
    )

    result = await db.execute(query)
    rows = result.all()

    return [
        TopExpenseItem(
            date=tx.date,
            description=tx.description,
            amount=abs(float(tx.amount)),
            category=cat_name,
            account_name=acc_name,
        )
        for tx, cat_name, acc_name in rows
    ]


@router.get("/insights", response_model=list[InsightItem])
async def get_insights(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    start_date: date | None = None,
    end_date: date | None = None,
):
    return await generate_insights(db, user.household_id, start_date, end_date)
