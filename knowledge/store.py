from __future__ import annotations

from typing import Any

from server.core.config import get_settings


def _collection_name(knowledge_base_id: str) -> str:
    # Chroma collection names: 3-63 chars, alnum + _ -
    safe = "".join(c if c.isalnum() or c in "_-" else "_" for c in knowledge_base_id)
    return f"kb_{safe}"[:63]


def _client():
    import chromadb
    from chromadb.config import Settings as ChromaSettings

    path = str(get_settings().chroma_dir)
    return chromadb.PersistentClient(path=path, settings=ChromaSettings(anonymized_telemetry=False))


def upsert_chunks(
    *,
    knowledge_base_id: str,
    doc_id: str,
    filename: str,
    workspace_id: str,
    chunks: list[str],
    embeddings: list[list[float]],
) -> int:
    if len(chunks) != len(embeddings):
        raise ValueError("chunks/embeddings length mismatch")
    if not chunks:
        return 0
    client = _client()
    col = client.get_or_create_collection(name=_collection_name(knowledge_base_id), metadata={"hnsw:space": "cosine"})
    ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
    metadatas = [
        {
            "doc_id": doc_id,
            "filename": filename,
            "chunk_index": i,
            "workspace_id": workspace_id,
            "knowledge_base_id": knowledge_base_id,
        }
        for i in range(len(chunks))
    ]
    # delete existing for doc then add
    try:
        col.delete(where={"doc_id": doc_id})
    except Exception:  # noqa: BLE001
        pass
    col.add(ids=ids, documents=chunks, embeddings=embeddings, metadatas=metadatas)
    return len(chunks)


def delete_document_vectors(*, knowledge_base_id: str, doc_id: str) -> None:
    client = _client()
    try:
        col = client.get_collection(name=_collection_name(knowledge_base_id))
    except Exception:  # noqa: BLE001
        return
    try:
        col.delete(where={"doc_id": doc_id})
    except Exception:  # noqa: BLE001
        pass


def delete_knowledge_base_vectors(*, knowledge_base_id: str) -> None:
    client = _client()
    name = _collection_name(knowledge_base_id)
    try:
        client.delete_collection(name)
    except Exception:  # noqa: BLE001
        pass


def query_knowledge(
    *,
    knowledge_base_ids: list[str],
    query_embedding: list[float],
    top_k: int = 5,
) -> list[dict[str, Any]]:
    if not knowledge_base_ids:
        return []
    client = _client()
    results: list[dict[str, Any]] = []
    per = max(1, int(top_k))
    for kb_id in knowledge_base_ids:
        try:
            col = client.get_collection(name=_collection_name(kb_id))
        except Exception:  # noqa: BLE001
            continue
        try:
            raw = col.query(query_embeddings=[query_embedding], n_results=per, include=["documents", "metadatas", "distances"])
        except Exception:  # noqa: BLE001
            continue
        docs = (raw.get("documents") or [[]])[0]
        metas = (raw.get("metadatas") or [[]])[0]
        dists = (raw.get("distances") or [[]])[0]
        for text, meta, dist in zip(docs, metas, dists, strict=False):
            score = 1.0 / (1.0 + float(dist)) if dist is not None else 0.0
            results.append(
                {
                    "text": text or "",
                    "filename": (meta or {}).get("filename"),
                    "doc_id": (meta or {}).get("doc_id"),
                    "knowledge_base_id": kb_id,
                    "score": round(score, 6),
                    "chunk_index": (meta or {}).get("chunk_index"),
                }
            )
    results.sort(key=lambda x: float(x.get("score") or 0), reverse=True)
    return results[:per]
