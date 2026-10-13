import chromadb

from app.config import settings

_collection = None


def get_collection():
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=settings.chroma_path)
        _collection = client.get_or_create_collection(
            "pdf_chunks", metadata={"hnsw:space": "cosine"})
    return _collection


def add_document(doc_id: str, filename: str, chunks: list[tuple[int, str]],
                 embeddings: list[list[float]]) -> None:
    get_collection().add(
        ids=[f"{doc_id}:{i}" for i in range(len(chunks))],
        documents=[t for _, t in chunks],
        embeddings=embeddings,
        metadatas=[{"doc_id": doc_id, "filename": filename, "page": p} for p, _ in chunks],
    )


def list_documents() -> list[dict]:
    data = get_collection().get(include=["metadatas"])
    docs: dict[str, dict] = {}
    for m in data["metadatas"]:
        d = docs.setdefault(m["doc_id"], {"id": m["doc_id"], "filename": m["filename"],
                                          "chunks": 0, "pages": 0})
        d["chunks"] += 1
        d["pages"] = max(d["pages"], m["page"])
    return list(docs.values())


def delete_document(doc_id: str) -> None:
    get_collection().delete(where={"doc_id": doc_id})


def query(embedding: list[float], k: int, doc_ids: list[str] | None) -> list[dict]:
    where = None
    if doc_ids:
        where = {"doc_id": doc_ids[0]} if len(doc_ids) == 1 else {"doc_id": {"$in": doc_ids}}
    res = get_collection().query(query_embeddings=[embedding], n_results=k, where=where)
    out = []
    for text, meta in zip(res["documents"][0], res["metadatas"][0]):
        out.append({"text": text, "page": meta["page"], "filename": meta["filename"],
                    "doc_id": meta["doc_id"]})
    return out
