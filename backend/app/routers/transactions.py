import hashlib
import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.account import Account
from app.models.category import Category, CategoryRule
from app.models.transaction import Transaction
from app.models.user import User
from app.routers.deps import get_current_user
from app.schemas.models import (
    TransactionResponse,
    TransactionCategoryUpdate,
    TransactionCreate,
    CategoryResponse,
    CategoryRuleCreate,
    CategoryRuleResponse,
)

router = APIRouter()


@router.get("", response_model=list[TransactionResponse])
async def list_transactions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    start_date: date | None = None,
    end_date: date | None = None,
    category_id: int | None = None,
    account_id: uuid.UUID | None = None,
    owner_id: uuid.UUID | None = None,
    limit: int = Query(default=200, le=1000),
    offset: int = Query(default=0, ge=0),
):
    query = (
        select(Transaction, Category.name.label("cat_name"))
        .outerjoin(Category, Transaction.category_id == Category.id)
        .join(Account, Transaction.account_id == Account.id)
        .where(Account.household_id == user.household_id)
    )

    if start_date:
        query = query.where(Transaction.date >= start_date)
    if end_date:
        query = query.where(Transaction.date <= end_date)
    if category_id:
        query = query.where(Transaction.category_id == category_id)
    if account_id:
        query = query.where(Transaction.account_id == account_id)
    if owner_id:
        query = query.where(Account.owner_id == owner_id)

    query = query.order_by(Transaction.date.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    rows = result.all()

    return [
        TransactionResponse(
            id=tx.id,
            account_id=tx.account_id,
            date=tx.date,
            description=tx.description,
            amount=float(tx.amount),
            type=tx.type,
            category_id=tx.category_id,
            category_name=cat_name,
            is_manual_category=tx.is_manual_category,
            source=tx.source,
            created_at=tx.created_at,
        )
        for tx, cat_name in rows
    ]


@router.patch("/{transaction_id}/category", response_model=TransactionResponse)
async def update_category(
    transaction_id: uuid.UUID,
    data: TransactionCategoryUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Transaction)
        .join(Account, Transaction.account_id == Account.id)
        .where(Transaction.id == transaction_id, Account.household_id == user.household_id)
    )
    tx = result.scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=404, detail="Transação não encontrada")

    tx.category_id = data.category_id
    tx.is_manual_category = True

    # Optionally create a rule for this pattern
    if data.create_rule:
        # Use first 3+ words of description as pattern
        words = tx.description.strip().split()
        pattern = " ".join(words[:3]).lower() if len(words) >= 3 else tx.description.lower()

        rule = CategoryRule(
            household_id=user.household_id,
            pattern=pattern,
            category_id=data.category_id,
            priority=200,  # user rules have high priority
        )
        db.add(rule)

    await db.commit()
    await db.refresh(tx)

    cat_result = await db.execute(select(Category.name).where(Category.id == tx.category_id))
    cat_name = cat_result.scalar_one_or_none()

    return TransactionResponse(
        id=tx.id,
        account_id=tx.account_id,
        date=tx.date,
        description=tx.description,
        amount=float(tx.amount),
        type=tx.type,
        category_id=tx.category_id,
        category_name=cat_name,
        is_manual_category=tx.is_manual_category,
        source=tx.source,
        created_at=tx.created_at,
    )


@router.post("", response_model=TransactionResponse)
async def create_transaction(
    data: TransactionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify account
    result = await db.execute(
        select(Account).where(
            Account.id == data.account_id,
            Account.household_id == user.household_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Conta não encontrada")

    tx_hash = hashlib.sha256(
        f"{data.account_id}|{data.date}|{data.description}|{data.amount:.2f}".encode()
    ).hexdigest()

    tx = Transaction(
        account_id=data.account_id,
        date=data.date,
        description=data.description,
        amount=data.amount,
        type=data.type,
        category_id=data.category_id,
        is_manual_category=data.category_id is not None,
        source="MANUAL",
        hash=tx_hash,
    )
    db.add(tx)
    await db.commit()
    await db.refresh(tx)

    cat_name = None
    if tx.category_id:
        cat_result = await db.execute(select(Category.name).where(Category.id == tx.category_id))
        cat_name = cat_result.scalar_one_or_none()

    return TransactionResponse(
        id=tx.id,
        account_id=tx.account_id,
        date=tx.date,
        description=tx.description,
        amount=float(tx.amount),
        type=tx.type,
        category_id=tx.category_id,
        category_name=cat_name,
        is_manual_category=tx.is_manual_category,
        source=tx.source,
        created_at=tx.created_at,
    )


@router.delete("/{transaction_id}")
async def delete_transaction(
    transaction_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Transaction)
        .join(Account, Transaction.account_id == Account.id)
        .where(Transaction.id == transaction_id, Account.household_id == user.household_id)
    )
    tx = result.scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=404, detail="Transação não encontrada")
    await db.delete(tx)
    await db.commit()
    return {"detail": "Transação removida"}


# --- Categories ---
@router.get("/categories", response_model=list[CategoryResponse])
async def list_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category).order_by(Category.name))
    return [CategoryResponse.model_validate(c) for c in result.scalars().all()]


@router.post("/categories/rules", response_model=CategoryRuleResponse)
async def create_rule(
    data: CategoryRuleCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rule = CategoryRule(
        household_id=user.household_id,
        pattern=data.pattern,
        category_id=data.category_id,
        priority=data.priority,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)

    cat_result = await db.execute(select(Category.name).where(Category.id == rule.category_id))
    cat_name = cat_result.scalar_one_or_none()

    return CategoryRuleResponse(
        id=rule.id,
        pattern=rule.pattern,
        category_id=rule.category_id,
        category_name=cat_name,
        priority=rule.priority,
    )
