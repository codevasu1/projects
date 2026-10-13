from collections.abc import Iterator

from google import genai
from google.genai import types

from app.config import settings

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


def embed(texts: list[str], task_type: str) -> list[list[float]]:
    vectors: list[list[float]] = []
    for i in range(0, len(texts), 90):
        batch = texts[i:i + 90]
        # Per-text Content objects: newer embedding models merge plain-string lists into one vector.
        res = _get_client().models.embed_content(
            model=settings.embed_model,
            contents=[types.Content(parts=[types.Part(text=t)]) for t in batch],
            config=types.EmbedContentConfig(task_type=task_type),
        )
        if len(res.embeddings) != len(batch):
            raise RuntimeError(
                f"Embedding count mismatch: got {len(res.embeddings)} for {len(batch)} texts")
        vectors.extend(e.values for e in res.embeddings)
    return vectors


def embed_documents(texts: list[str]) -> list[list[float]]:
    return embed(texts, "RETRIEVAL_DOCUMENT")


def embed_query(text: str) -> list[float]:
    return embed([text], "RETRIEVAL_QUERY")[0]


SYSTEM = (
    "You answer questions using ONLY the provided PDF excerpts. "
    "If the answer is not in the excerpts, say you could not find it in the document. "
    "Mention page numbers like (p. 3) when relevant."
)


def stream_answer(question: str, history: list[dict], contexts: list[dict]) -> Iterator[str]:
    context_text = "\n\n".join(
        f"[{c['filename']} p.{c['page']}]\n{c['text']}" for c in contexts
    )
    contents = [
        types.Content(role="user" if m["role"] == "user" else "model",
                      parts=[types.Part(text=m["content"])])
        for m in history
    ]
    contents.append(types.Content(role="user", parts=[types.Part(
        text=f"Excerpts:\n{context_text}\n\nQuestion: {question}")]))
    for chunk in _get_client().models.generate_content_stream(
        model=settings.gen_model,
        contents=contents,
        config=types.GenerateContentConfig(system_instruction=SYSTEM),
    ):
        if chunk.text:
            yield chunk.text
