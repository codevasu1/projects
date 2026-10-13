import json
from typing import Literal

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.config import settings
from app.services import llm, vectorstore

router = APIRouter(prefix="/api", tags=["chat"])


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    history: list[Message] = []
    doc_ids: list[str] | None = None


def _sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/chat")
def chat(req: ChatRequest):
    def gen():
        try:
            contexts = vectorstore.query(llm.embed_query(req.question),
                                         settings.top_k, req.doc_ids)
            if not contexts:
                yield _sse("token", "No documents are available. Please upload a PDF first.")
                yield _sse("done", {})
                return
            sources = [{"filename": c["filename"], "page": c["page"],
                        "snippet": c["text"][:200]} for c in contexts]
            yield _sse("sources", sources)
            history = [m.model_dump() for m in req.history[-10:]]
            for tok in llm.stream_answer(req.question, history, contexts):
                yield _sse("token", tok)
            yield _sse("done", {})
        except Exception as e:  # surface failure to the client stream
            yield _sse("error", str(e))

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache"})
