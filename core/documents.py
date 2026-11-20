"""Safe text extraction for user-provided PDF context."""

from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError

MAX_PDF_BYTES = 10 * 1024 * 1024
MAX_PDF_PAGES = 100
MAX_PDF_TEXT_CHARS = 25_000


def extract_pdf_text(pdf_bytes: bytes) -> tuple[str, bool]:
    if not pdf_bytes:
        raise ValueError("The uploaded PDF is empty.")
    if len(pdf_bytes) > MAX_PDF_BYTES:
        raise ValueError("PDFs must be 10 MB or smaller.")

    try:
        reader = PdfReader(BytesIO(pdf_bytes), strict=False)
        if reader.is_encrypted:
            raise ValueError("Encrypted PDFs are not supported.")
        if len(reader.pages) > MAX_PDF_PAGES:
            raise ValueError(f"PDFs must have {MAX_PDF_PAGES} pages or fewer.")

        pages = []
        total_chars = 0
        truncated = False
        for page in reader.pages:
            page_text = page.extract_text() or ""
            if not page_text.strip():
                continue

            separator = "\n\n" if pages else ""
            remaining = MAX_PDF_TEXT_CHARS - total_chars - len(separator)
            if remaining <= 0:
                truncated = True
                break

            pages.append(separator + page_text[:remaining])
            total_chars += len(separator) + min(len(page_text), remaining)
            if len(page_text) > remaining:
                truncated = True
                break
    except PdfReadError as exc:
        raise ValueError("The PDF could not be read. Check that it is a valid PDF.") from exc

    text = "".join(pages).strip()
    if not text:
        raise ValueError(
            "No selectable text was found. Scanned PDFs need OCR before upload."
        )
    return text, truncated
