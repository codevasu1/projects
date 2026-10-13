import io

from pypdf import PdfReader


def extract_pages(data: bytes) -> list[tuple[int, str]]:
    """Return [(page_number, text)] for pages that contain text."""
    reader = PdfReader(io.BytesIO(data))
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            pages.append((i, text))
    return pages


def chunk_pages(pages: list[tuple[int, str]], size: int, overlap: int) -> list[tuple[int, str]]:
    """Split each page into overlapping chunks, keeping the page number."""
    step = max(size - overlap, 1)
    chunks = []
    for page, text in pages:
        for start in range(0, len(text), step):
            piece = text[start:start + size].strip()
            if piece:
                chunks.append((page, piece))
            if start + size >= len(text):
                break
    return chunks
