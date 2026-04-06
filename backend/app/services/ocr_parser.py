from io import BytesIO

from PIL import Image

from app.schemas.models import TransactionPreview
from app.services.pdf_parser import _extract_transactions_from_text


def parse_image(file_content: bytes) -> list[TransactionPreview]:
    try:
        import pytesseract
    except ImportError:
        return []

    image = Image.open(BytesIO(file_content))

    # OCR with Portuguese language
    text = pytesseract.image_to_string(image, lang="por")

    return _extract_transactions_from_text(text)
