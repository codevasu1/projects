import uuid

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool

from app.config import settings
from app.services import llm, pdf, vectorstore

router = APIRouter(prefix="/api/documents", tags=["documents"])


def _ingest(data: bytes, filename: str) -> dict:
    try:
        pages = pdf.extract_pages(data)
    except Exception:
        raise HTTPException(400, "Could not read PDF")
    chunks = pdf.chunk_pages(pages, settings.chunk_size, settings.chunk_overlap)
    if not chunks:
        raise HTTPException(422, "No extractable text found (scanned PDF?)")
    doc_id = uuid.uuid4().hex
    embeddings = llm.embed_documents([t for _, t in chunks])
    vectorstore.add_document(doc_id, filename, chunks, embeddings)
    return {"id": doc_id, "filename": filename, "chunks": len(chunks),
            "pages": max(p for p, _ in chunks)}


@router.post("", status_code=201)
async def upload(file: UploadFile):
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported")
    data = await file.read()
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"File exceeds {settings.max_upload_mb} MB")
    if not data.startswith(b"%PDF"):
        raise HTTPException(400, "File is not a valid PDF")
    return await run_in_threadpool(_ingest, data, file.filename)


@router.get("")
def list_docs():
    return vectorstore.list_documents()


@router.delete("/{doc_id}", status_code=204)
def delete(doc_id: str):
    vectorstore.delete_document(doc_id)
