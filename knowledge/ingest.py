from __future__ import annotations

from pathlib import Path

from knowledge.chunking import chunk_text
from knowledge.embeddings import embed_texts
from knowledge.extract import extract_text
from knowledge.store import upsert_chunks
from server.core.config import get_settings


def ingest_file(
    *,
    knowledge_base_id: str,
    workspace_id: str,
    doc_id: str,
    filename: str,
    file_path: str | Path,
) -> int:
    settings = get_settings()
    text = extract_text(file_path)
    chunks = chunk_text(text, chunk_size=settings.rag_chunk_size, overlap=settings.rag_chunk_overlap)
    if not chunks:
        raise ValueError("No text chunks produced from document")
    vectors = embed_texts(chunks)
    return upsert_chunks(
        knowledge_base_id=knowledge_base_id,
        doc_id=doc_id,
        filename=filename,
        workspace_id=workspace_id,
        chunks=chunks,
        embeddings=vectors,
    )
