import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

export interface Cargo {
  id: string
  nome: string
  vagas: number | null
  salario: number | null
  requisitos: string | null
}

export interface Concurso {
  id: string
  instituicao: string
  orgao: string | null
  status: string
  link_edital: string
  pdf_url: string | null
  salario_maximo: number | null
  data_encerramento: string | null
  created_at: string
  cargos?: Cargo[]
}

export interface PaginatedConcursos {
  total: number
  page: number
  page_size: number
  items: Concurso[]
}

export interface ConcursoFilters {
  orgao?: string
  status?: string
  salario_min?: number
  salario_max?: number
  page?: number
  page_size?: number
}

export async function getConcursos(filters: ConcursoFilters = {}): Promise<PaginatedConcursos> {
  const params = new URLSearchParams()
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== '' && value !== null) {
      params.set(key, String(value))
    }
  })
  const response = await apiClient.get<PaginatedConcursos>(`/concursos?${params}`)
  return response.data
}

export async function getConcurso(id: string): Promise<Concurso> {
  const response = await apiClient.get<Concurso>(`/concursos/${id}`)
  return response.data
}

export function streamChat(
  concursoId: string,
  question: string,
  onChunk: (text: string) => void,
  onDone: () => void,
  onError: (error: string) => void
): () => void {
  const controller = new AbortController()

  fetch(`${BASE_URL}/chat/${concursoId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        onError(`HTTP error: ${response.status}`)
        return
      }

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()

      if (!reader) {
        onError('No response body')
        return
      }

      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              if (data.error) {
                onError(data.error)
                return
              }
              if (data.done) {
                onDone()
                return
              }
              if (data.text) {
                onChunk(data.text)
              }
            } catch {
              // Ignore parse errors on partial chunks
            }
          }
        }
      }
      onDone()
    })
    .catch((err) => {
      if (err.name !== 'AbortError') {
        onError(err.message)
      }
    })

  return () => controller.abort()
}
