from datetime import date
from io import BytesIO

from ofxparse import OfxParser

from app.schemas.models import TransactionPreview


def parse_ofx(file_content: bytes) -> list[TransactionPreview]:
    ofx = OfxParser.parse(BytesIO(file_content))
    transactions = []

    for tx in ofx.account.statement.transactions:
        amount = float(tx.amount)
        tx_type = "INCOME" if amount > 0 else "EXPENSE"

        transactions.append(TransactionPreview(
            date=tx.date.date() if hasattr(tx.date, 'date') else tx.date,
            description=tx.payee or tx.memo or "Sem descrição",
            amount=amount,
            type=tx_type,
        ))

    return transactions
