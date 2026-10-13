import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService, ChatMessage, DocInfo } from './api.service';

@Component({
  selector: 'app-root',
  imports: [FormsModule],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App implements OnInit {
  private api = inject(ApiService);

  docs = signal<DocInfo[]>([]);
  selected = signal<Set<string>>(new Set());
  messages = signal<ChatMessage[]>([]);
  uploading = signal(false);
  busy = signal(false);
  uploadError = signal('');
  question = '';

  ngOnInit() {
    this.refresh();
  }

  refresh() {
    this.api.listDocs().subscribe((d) => this.docs.set(d));
  }

  onFile(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    input.value = '';
    if (!file) return;
    this.uploading.set(true);
    this.uploadError.set('');
    this.api.upload(file).subscribe({
      next: () => {
        this.uploading.set(false);
        this.refresh();
      },
      error: (e) => {
        this.uploading.set(false);
        this.uploadError.set(e.error?.detail ?? 'Upload failed');
      },
    });
  }

  toggle(id: string) {
    const s = new Set(this.selected());
    if (s.has(id)) s.delete(id);
    else s.add(id);
    this.selected.set(s);
  }

  remove(id: string) {
    this.api.deleteDoc(id).subscribe(() => {
      const s = new Set(this.selected());
      s.delete(id);
      this.selected.set(s);
      this.refresh();
    });
  }

  async send() {
    const q = this.question.trim();
    if (!q || this.busy()) return;
    this.question = '';
    const history = this.messages();
    const answer: ChatMessage = { role: 'assistant', content: '' };
    this.messages.set([...history, { role: 'user', content: q }, answer]);
    this.busy.set(true);
    const update = (fn: (m: ChatMessage) => ChatMessage) =>
      this.messages.update((list) => [...list.slice(0, -1), fn(list[list.length - 1])]);
    try {
      await this.api.chat(q, history, [...this.selected()], {
        onSources: (sources) => update((m) => ({ ...m, sources })),
        onToken: (t) => update((m) => ({ ...m, content: m.content + t })),
        onError: (msg) => update((m) => ({ ...m, content: msg, error: true })),
      });
    } catch {
      update((m) => ({ ...m, content: 'Could not reach the server.', error: true }));
    } finally {
      this.busy.set(false);
    }
  }
}
