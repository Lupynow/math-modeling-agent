from __future__ import annotations

import hashlib
import io
from pathlib import Path

from pypdf import PdfReader


class DocumentParseError(ValueError):
    pass


SUPPORTED_SUFFIXES = {".pdf", ".txt", ".md", ".markdown"}


def sanitize_filename(filename: str) -> str:
    safe = Path(filename).name.strip()
    if not safe or safe in {".", ".."}:
        raise DocumentParseError("Invalid filename.")
    return safe[:255]


def parse_document(filename: str, content: bytes, max_bytes: int) -> tuple[str, str, str]:
    safe_name = sanitize_filename(filename)
    suffix = Path(safe_name).suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise DocumentParseError("Only PDF, TXT, MD, and Markdown files are supported.")
    if not content:
        raise DocumentParseError("The uploaded document is empty.")
    if len(content) > max_bytes:
        raise DocumentParseError(f"The uploaded document exceeds {max_bytes} bytes.")

    if suffix == ".pdf":
        try:
            reader = PdfReader(io.BytesIO(content))
            text = "\n\n".join((page.extract_text() or "").strip() for page in reader.pages)
        except Exception as exc:
            raise DocumentParseError("The PDF could not be parsed.") from exc
        media_type = "application/pdf"
        if not text.strip():
            raise DocumentParseError(
                "The PDF contains no extractable text. Run OCR before uploading a scanned PDF."
            )
    else:
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise DocumentParseError("Text documents must use UTF-8 encoding.") from exc
        media_type = "text/markdown" if suffix in {".md", ".markdown"} else "text/plain"

    cleaned = "\n".join(line.rstrip() for line in text.splitlines()).strip()
    if len(cleaned) < 20:
        raise DocumentParseError("The document does not contain enough text to analyze.")
    return cleaned, media_type, hashlib.sha256(content).hexdigest()
