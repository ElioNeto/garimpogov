import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

const api = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

// ─── Types ──────────────────────────────────────────────────────────────────

export interface Cargo {
  id: string;
  nome: string;
  vagas: number | null;
  salario: number | null;
  requisitos: string | null;
}

export interface Concurso {
  id: string;
  instituicao: string;
  orgao: string | null;
  status: string;
  link_edital: string;
  pdf_url: string | null;
  salario_maximo: number | null;
  data_encerramento: string | null;
  created_at: string;
  cargos?: Cargo[];
}

export interface PaginatedResponse<T> {
  total: number;
  page: number;
  page_size: number;
  items: T[];
}

export interface ConcursoFilters {
  orgao?: string;
  status?: string;
  salario_min?: number;
  salario_max?: number;
  data_encerramento_antes?: string;
  page?: number;
  page_size?: number;
}

// ─── API Functions ───────────────────────────────────────────────────────────

export async function getConcursos(
  filters: ConcursoFilters = {}
): Promise<PaginatedResponse<Concurso>> {
  const params: Record<string, string | number> = {};
  if (filters.orgao) params.orgao = filters.orgao;
  if (filters.status) params.status = filters.status;
  if (filters.salario_min != null) params.salario_min = filters.salario_min;
  if (filters.salario_max != null) params.salario_max = filters.salario_max;
  if (filters.data_encerramento_antes) params.data_encerramento_antes = filters.data_encerramento_antes;
  if (filters.page) params.page = filters.page;
  if (filters.page_size) params.page_size = filters.page_size;

  const { data } = await api.get<PaginatedResponse<Concurso>>('/concursos', { params });
  return data;
}

export async function getConcurso(id: string): Promise<Concurso> {
  const { data } = await api.get<Concurso>(`/concursos/${id}`);
  return data;
}

/**
 * Streams a chat response via Server-Sent Events.
 * Returns an abort function to cancel the stream.
 */
export function streamChat(
  concursoId: string,
  question: string,
  onChunk: (text: string) => void,
  onDone: () => void,
  onError: (error: string) => void
): () => void {
  const controller = new AbortController();

  (async () => {
    try {
      const response = await fetch(`${BASE_URL}/chat/${concursoId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
        signal: controller.signal,
      });

      if (!response.ok) {
        onError(`HTTP ${response.status}: ${response.statusText}`);
        return;
      }

      const reader = response.body?.getReader();
      if (!reader) { onError('Stream indisponível'); return; }

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          try {
            const payload = JSON.parse(line.slice(6));
            if (payload.error) { onError(payload.error); return; }
            if (payload.done) { onDone(); return; }
            if (payload.text) onChunk(payload.text);
          } catch {
            // skip malformed line
          }
        }
      }
      onDone();
    } catch (err: unknown) {
      if ((err as Error).name !== 'AbortError') {
        onError(err instanceof Error ? err.message : 'Erro desconhecido');
      }
    }
  })();

  return () => controller.abort();
}
