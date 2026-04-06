import re
from datetime import datetime
from io import BytesIO

import pdfplumber

from app.schemas.models import TransactionPreview


def _extract_transactions_from_text(text: str) -> list[TransactionPreview]:
    """Extract transactions using common Brazilian bank statement patterns."""
    transactions = []

    # Pattern: DD/MM/YYYY or DD/MM Description Value (with optional minus)
    patterns = [
        # DD/MM/YYYY ... description ... -1.234,56 or 1.234,56
        r"(\d{2}/\d{2}/\d{4})\s+(.+?)\s+(-?\s*[\d.]+,\d{2})\s*$",
        # DD/MM ... description ... -1.234,56
        r"(\d{2}/\d{2})\s+(.+?)\s+(-?\s*[\d.]+,\d{2})\s*$",
        # DD/MM/YYYY description R$ 1.234,56
        r"(\d{2}/\d{2}/\d{4})\s+(.+?)\s+R\$\s*(-?\s*[\d.]+,\d{2})",
        # DD MMM YYYY description R$ 1.234,56 (Nubank style)
        r"(\d{2}\s+\w{3}\s+\d{4})\s+(.+?)\s+R?\$?\s*(-?\s*[\d.]+,\d{2})",
    ]

    current_year = datetime.now().year

    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue

        for pattern in patterns:
            match = re.match(pattern, line)
            if match:
                date_str, description, amount_str = match.groups()
                description = description.strip()

                # Skip header-like lines
                if any(skip in description.lower() for skip in ["saldo", "total", "subtotal", "anterior"]):
                    continue

                # Parse date
                dt = None
                for fmt in ("%d/%m/%Y", "%d/%m", "%d %b %Y"):
                    try:
                        dt = datetime.strptime(date_str.strip(), fmt).date()
                        if dt.year == 1900:  # DD/MM without year
                            dt = dt.replace(year=current_year)
                        break
                    except ValueError:
                        continue

                if not dt:
                    continue

                # Parse amount
                amount_str = amount_str.strip().replace(" ", "").replace(".", "").replace(",", ".")
                try:
                    amount = float(amount_str)
                except ValueError:
                    continue

                tx_type = "INCOME" if amount > 0 else "EXPENSE"
                transactions.append(TransactionPreview(
                    date=dt,
                    description=description,
                    amount=amount,
                    type=tx_type,
                ))
                break

    return transactions


def parse_pdf(file_content: bytes) -> list[TransactionPreview]:
    all_transactions = []

    with pdfplumber.open(BytesIO(file_content)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                txs = _extract_transactions_from_text(text)
                all_transactions.extend(txs)

    return all_transactions
