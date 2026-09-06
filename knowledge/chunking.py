from __future__ import annotations


def chunk_text(text: str, *, chunk_size: int = 800, overlap: int = 120) -> list[str]:
    cleaned = (text or "").strip()
    if not cleaned:
        return []
    size = max(100, int(chunk_size))
    ov = max(0, min(int(overlap), size // 2))
    chunks: list[str] = []
    start = 0
    n = len(cleaned)
    while start < n:
        end = min(n, start + size)
        piece = cleaned[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= n:
            break
        start = max(0, end - ov)
    return chunks
