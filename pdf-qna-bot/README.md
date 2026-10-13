# PDF QnA Bot

Angular + FastAPI RAG chatbot: upload PDFs, ask questions, get streamed answers with page citations
(Gemini for embeddings/generation, ChromaDB for vectors).

## Backend
```
cd backend
python -m venv .venv ; .\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # set GEMINI_API_KEY
uvicorn app.main:app --reload
pytest                   # tests (Gemini mocked)
```

## Frontend
```
cd frontend
npm install
npm start -- --proxy-config proxy.conf.json   # http://localhost:4200
```

API: `POST/GET /api/documents`, `DELETE /api/documents/{id}`, `POST /api/chat` (SSE: `sources`, `token`, `done`, `error`).




