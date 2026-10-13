import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.services import llm, pdf, vectorstore


def make_pdf(text: str) -> bytes:
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = b"%PDF-1.4\n"
    offsets = []
    for i, o in enumerate(objs, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    for off in offsets:
        out += b"%010d 00000 n \n" % off
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF" % (len(objs) + 1, xref)
    return out


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "chroma_path", str(tmp_path / "chroma"))
    monkeypatch.setattr(vectorstore, "_collection", None)
    monkeypatch.setattr(llm, "embed_documents", lambda texts: [[1.0, 0.0, 0.0]] * len(texts))
    monkeypatch.setattr(llm, "embed_query", lambda t: [1.0, 0.0, 0.0])
    monkeypatch.setattr(llm, "stream_answer", lambda q, h, c: iter(["Hello ", "world"]))
    return TestClient(app)


def test_chunking():
    chunks = pdf.chunk_pages([(1, "a" * 2500)], 1000, 200)
    assert [p for p, _ in chunks] == [1, 1, 1]


def test_upload_chat_delete(client):
    r = client.post("/api/documents", files={"file": ("a.pdf", make_pdf("Cats are great"), "application/pdf")})
    assert r.status_code == 201, r.text
    doc = r.json()
    assert client.get("/api/documents").json()[0]["id"] == doc["id"]

    r = client.post("/api/chat", json={"question": "What?", "doc_ids": [doc["id"]]})
    assert "event: sources" in r.text and '"page": 1' in r.text
    assert 'data: "Hello "' in r.text and "event: done" in r.text

    assert client.delete(f"/api/documents/{doc['id']}").status_code == 204
    assert client.get("/api/documents").json() == []


def test_rejects_non_pdf(client):
    r = client.post("/api/documents", files={"file": ("a.txt", b"hi", "text/plain")})
    assert r.status_code == 400
    r = client.post("/api/documents", files={"file": ("a.pdf", b"not pdf", "application/pdf")})
    assert r.status_code == 400
