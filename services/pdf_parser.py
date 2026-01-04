import pdfplumber
from typing import Optional
import io

def extract_text_from_bytes(file_bytes: bytes) -> str:
    """Extract all text from a PDF given as bytes."""
    text = ""
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text += page_text + "\n"
    return text.strip()
