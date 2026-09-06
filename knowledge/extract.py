from __future__ import annotations

from pathlib import Path


SUPPORTED_EXTENSIONS = {".md", ".txt", ".pdf"}


def extract_text(path: str | Path) -> str:
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported knowledge file type: {suffix}")
    if suffix in {".md", ".txt"}:
        return p.read_text(encoding="utf-8", errors="replace")
    from pypdf import PdfReader

    reader = PdfReader(str(p))
    parts: list[str] = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    text = "\n".join(parts).strip()
    if not text:
        raise ValueError("PDF extracted empty text (OCR not supported)")
    return text
