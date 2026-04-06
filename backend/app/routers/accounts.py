import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.account import Account
from app.routers.deps import get_current_user
from app.models.user import User
from app.schemas.models import AccountCreate, AccountResponse

router = APIRouter()


@router.get("", response_model=list[AccountResponse])
async def list_accounts(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Account).where(Account.household_id == user.household_id)
    )
    return [AccountResponse.model_validate(a) for a in result.scalars().all()]


@router.post("", response_model=AccountResponse)
async def create_account(
    data: AccountCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    account = Account(
        household_id=user.household_id,
        owner_id=data.owner_id,
        bank_name=data.bank_name,
        type=data.type,
        name=data.name,
        last_four_digits=data.last_four_digits,
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return AccountResponse.model_validate(account)


@router.delete("/{account_id}")
async def delete_account(
    account_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Account).where(
            Account.id == account_id,
            Account.household_id == user.household_id,
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    await db.delete(account)
    await db.commit()
    return {"detail": "Conta removida"}
