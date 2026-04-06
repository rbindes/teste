import csv
import io
from datetime import datetime, date

from app.schemas.models import TransactionPreview


def _parse_amount_br(value: str) -> float:
    """Parse Brazilian currency format: 1.234,56 or -1.234,56"""
    clean = value.strip().replace("R$", "").replace(" ", "")
    clean = clean.replace(".", "").replace(",", ".")
    return float(clean)


def _detect_bank(header: list[str], rows: list[list[str]]) -> str:
    header_lower = [h.strip().lower() for h in header]

    if "title" in header_lower or "título" in header_lower:
        return "nubank"
    if "historico" in header_lower or "histórico" in header_lower:
        return "bb"
    if "lançamento" in header_lower or "lancamento" in header_lower:
        return "bradesco"
    return "generic"


def _parse_nubank(rows: list[list[str]], header: list[str]) -> list[TransactionPreview]:
    """Nubank CSV: date, title/category, amount"""
    transactions = []
    header_lower = [h.strip().lower() for h in header]

    date_col = next((i for i, h in enumerate(header_lower) if h in ("date", "data")), 0)
    desc_col = next((i for i, h in enumerate(header_lower) if h in ("title", "titulo", "título", "description", "descrição")), 1)
    amount_col = next((i for i, h in enumerate(header_lower) if h in ("amount", "valor")), -1)

    for row in rows:
        if len(row) < 3:
            continue
        try:
            dt_str = row[date_col].strip()
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
                try:
                    dt = datetime.strptime(dt_str, fmt).date()
                    break
                except ValueError:
                    continue
            else:
                continue

            amount = _parse_amount_br(row[amount_col])
            tx_type = "INCOME" if amount > 0 else "EXPENSE"

            transactions.append(TransactionPreview(
                date=dt,
                description=row[desc_col].strip(),
                amount=amount,
                type=tx_type,
            ))
        except (ValueError, IndexError):
            continue

    return transactions


def _parse_generic(rows: list[list[str]], header: list[str]) -> list[TransactionPreview]:
    """Generic CSV parser - tries to find date, description, amount columns."""
    transactions = []
    header_lower = [h.strip().lower() for h in header]

    date_col = next((i for i, h in enumerate(header_lower) if "dat" in h), 0)
    desc_col = next((i for i, h in enumerate(header_lower) if any(k in h for k in ("desc", "hist", "lanc", "title", "titul"))), 1)
    amount_col = next((i for i, h in enumerate(header_lower) if any(k in h for k in ("valor", "amount", "quantia"))), -1)

    for row in rows:
        if len(row) < max(date_col, desc_col, amount_col) + 1:
            continue
        try:
            dt_str = row[date_col].strip()
            for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y"):
                try:
                    dt = datetime.strptime(dt_str, fmt).date()
                    break
                except ValueError:
                    continue
            else:
                continue

            amount = _parse_amount_br(row[amount_col])
            tx_type = "INCOME" if amount > 0 else "EXPENSE"

            transactions.append(TransactionPreview(
                date=dt,
                description=row[desc_col].strip(),
                amount=amount,
                type=tx_type,
            ))
        except (ValueError, IndexError):
            continue

    return transactions


def parse_csv(file_content: bytes) -> list[TransactionPreview]:
    text = file_content.decode("utf-8", errors="replace")
    # Try different delimiters
    for delimiter in [",", ";", "\t"]:
        reader = csv.reader(io.StringIO(text), delimiter=delimiter)
        rows = list(reader)
        if len(rows) > 1 and len(rows[0]) >= 3:
            break
    else:
        return []

    header = rows[0]
    data_rows = rows[1:]
    bank = _detect_bank(header, data_rows)

    if bank == "nubank":
        return _parse_nubank(data_rows, header)
    return _parse_generic(data_rows, header)
