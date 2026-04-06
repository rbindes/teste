import hashlib
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.account import Account
from app.models.transaction import Transaction
from app.models.upload import Upload
from app.models.user import User
from app.routers.deps import get_current_user
from app.schemas.models import (
    TransactionPreview,
    UploadPreviewResponse,
    UploadConfirmResponse,
    UploadHistoryResponse,
)
from app.services.categorizer import categorize_transaction
from app.services.ofx_parser import parse_ofx
from app.services.csv_parser import parse_csv
from app.services.pdf_parser import parse_pdf
from app.services.ocr_parser import parse_image

router = APIRouter()

# Temporary storage for previews (in production, use Redis or DB)
_preview_cache: dict[str, dict] = {}


def _detect_file_type(filename: str, content_type: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext == "ofx" or ext == "qfx":
        return "OFX"
    if ext == "csv":
        return "CSV"
    if ext == "pdf":
        return "PDF"
    if ext in ("jpg", "jpeg", "png", "tiff", "bmp"):
        return "IMAGE"
    if "pdf" in content_type:
        return "PDF"
    if "image" in content_type:
        return "IMAGE"
    return "CSV"  # default fallback


def _make_hash(account_id: uuid.UUID, date_val, description: str, amount: float) -> str:
    raw = f"{account_id}|{date_val}|{description}|{amount:.2f}"
    return hashlib.sha256(raw.encode()).hexdigest()


@router.post("/upload", response_model=UploadPreviewResponse)
async def upload_file(
    file: Annotated[UploadFile, File()],
    account_id: Annotated[uuid.UUID, Form()],
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify account belongs to household
    result = await db.execute(
        select(Account).where(
            Account.id == account_id,
            Account.household_id == user.household_id,
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Conta não encontrada")

    content = await file.read()
    file_type = _detect_file_type(file.filename or "", file.content_type or "")

    # Parse based on file type
    if file_type == "OFX":
        transactions = parse_ofx(content)
    elif file_type == "CSV":
        transactions = parse_csv(content)
    elif file_type == "PDF":
        transactions = parse_pdf(content)
    elif file_type == "IMAGE":
        transactions = parse_image(content)
    else:
        raise HTTPException(status_code=400, detail=f"Tipo de arquivo não suportado: {file_type}")

    if not transactions:
        raise HTTPException(status_code=400, detail="Nenhuma transação encontrada no arquivo")

    # Create upload record
    upload = Upload(
        account_id=account_id,
        uploaded_by=user.id,
        filename=file.filename or "unknown",
        file_type=file_type,
    )
    db.add(upload)
    await db.commit()
    await db.refresh(upload)

    # Cache preview
    _preview_cache[str(upload.id)] = {
        "transactions": transactions,
        "account_id": account_id,
    }

    return UploadPreviewResponse(
        upload_id=upload.id,
        filename=upload.filename,
        file_type=file_type,
        transactions=transactions,
        total_count=len(transactions),
    )


@router.get("/{upload_id}/preview", response_model=UploadPreviewResponse)
async def get_preview(
    upload_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cached = _preview_cache.get(str(upload_id))
    if not cached:
        raise HTTPException(status_code=404, detail="Preview expirado. Faça upload novamente.")

    result = await db.execute(select(Upload).where(Upload.id == upload_id))
    upload = result.scalar_one_or_none()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload não encontrado")

    return UploadPreviewResponse(
        upload_id=upload.id,
        filename=upload.filename,
        file_type=upload.file_type,
        transactions=cached["transactions"],
        total_count=len(cached["transactions"]),
    )


@router.post("/{upload_id}/confirm", response_model=UploadConfirmResponse)
async def confirm_import(
    upload_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cached = _preview_cache.get(str(upload_id))
    if not cached:
        raise HTTPException(status_code=404, detail="Preview expirado. Faça upload novamente.")

    result = await db.execute(select(Upload).where(Upload.id == upload_id))
    upload = result.scalar_one_or_none()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload não encontrado")

    account_id = cached["account_id"]
    transactions_preview: list[TransactionPreview] = cached["transactions"]

    imported = 0
    skipped = 0

    for tx_preview in transactions_preview:
        tx_hash = _make_hash(account_id, tx_preview.date, tx_preview.description, tx_preview.amount)

        # Check duplicate
        existing = await db.execute(
            select(Transaction).where(Transaction.hash == tx_hash)
        )
        if existing.scalar_one_or_none():
            skipped += 1
            continue

        # Auto-categorize
        category_id = await categorize_transaction(
            tx_preview.description, user.household_id, db
        )

        tx = Transaction(
            account_id=account_id,
            date=tx_preview.date,
            description=tx_preview.description,
            amount=tx_preview.amount,
            type=tx_preview.type,
            category_id=category_id,
            source=upload.file_type,
            upload_id=upload_id,
            hash=tx_hash,
        )
        db.add(tx)
        imported += 1

    upload.transactions_imported = imported
    upload.transactions_skipped = skipped
    await db.commit()

    # Clean cache
    _preview_cache.pop(str(upload_id), None)

    return UploadConfirmResponse(
        upload_id=upload_id,
        transactions_imported=imported,
        transactions_skipped=skipped,
    )


@router.get("/history", response_model=list[UploadHistoryResponse])
async def upload_history(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Upload, Account.name)
        .join(Account, Upload.account_id == Account.id)
        .where(Account.household_id == user.household_id)
        .order_by(Upload.created_at.desc())
        .limit(50)
    )
    rows = result.all()
    return [
        UploadHistoryResponse(
            id=upload.id,
            filename=upload.filename,
            file_type=upload.file_type,
            transactions_imported=upload.transactions_imported,
            transactions_skipped=upload.transactions_skipped,
            created_at=upload.created_at,
            account_name=account_name,
        )
        for upload, account_name in rows
    ]
