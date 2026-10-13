import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';

export interface DocInfo {
  id: string;
  filename: string;
  pages: number;
  chunks: number;
}
export interface Source {
  filename: string;
  page: number;
  snippet: string;
}
export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
  error?: boolean;
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  private http = inject(HttpClient);

  listDocs() {
    return this.http.get<DocInfo[]>('/api/documents');
  }

  upload(file: File) {
    const form = new FormData();
    form.append('file', file);
    return this.http.post<DocInfo>('/api/documents', form);
  }

  deleteDoc(id: string) {
    return this.http.delete<void>(`/api/documents/${id}`);
  }

  /** Streams a chat answer over SSE using fetch (POST body is needed). */
  async chat(
    question: string,
    history: ChatMessage[],
    docIds: string[],
    handlers: {
      onSources: (s: Source[]) => void;
      onToken: (t: string) => void;
      onError: (m: string) => void;
    },
    signal?: AbortSignal,
  ): Promise<void> {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question,
        history: history.map(({ role, content }) => ({ role, content })),
        doc_ids: docIds.length ? docIds : null,
      }),
      signal,
    });
    if (!res.ok || !res.body) {
      handlers.onError(`Request failed (${res.status})`);
      return;
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let idx: number;
      while ((idx = buffer.indexOf('\n\n')) >= 0) {
        const raw = buffer.slice(0, idx);
        buffer = buffer.slice(idx + 2);
        let event = 'message';
        let data = '';
        for (const line of raw.split('\n')) {
          if (line.startsWith('event: ')) event = line.slice(7);
          else if (line.startsWith('data: ')) data += line.slice(6);
        }
        if (!data) continue;
        const payload = JSON.parse(data);
        if (event === 'sources') handlers.onSources(payload);
        else if (event === 'token') handlers.onToken(payload);
        else if (event === 'error') handlers.onError(payload);
      }
    }
  }
}
