import { useEffect, useState } from 'react'
import { Search, Sparkles } from 'lucide-react'
import FiltersPanel from '../components/FiltersPanel'
import ConcursoList from '../components/ConcursoList'
import ChatModal from '../components/ChatModal'
import { getConcursos } from '../services/api'
import type { Concurso, ConcursoFilters, PaginatedConcursos } from '../services/api'

export default function HomePage() {
  const [data, setData] = useState<PaginatedConcursos | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [filters, setFilters] = useState<ConcursoFilters>({ page: 1 })
  const [selectedConcurso, setSelectedConcurso] = useState<Concurso | null>(null)
  const [chatOpen, setChatOpen] = useState(false)

  async function fetchConcursos(newFilters: ConcursoFilters) {
    setLoading(true)
    setError(null)
    try {
      const result = await getConcursos(newFilters)
      setData(result)
    } catch (err) {
      setError('Erro ao carregar concursos. Verifique a conexao com a API.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchConcursos(filters)
  }, [])

  function handleFilter(newFilters: ConcursoFilters) {
    const merged = { ...filters, ...newFilters, page: 1 }
    setFilters(merged)
    fetchConcursos(merged)
  }

  function handlePageChange(page: number) {
    const merged = { ...filters, page }
    setFilters(merged)
    fetchConcursos(merged)
  }

  function handleChat(concurso: Concurso) {
    setSelectedConcurso(concurso)
    setChatOpen(true)
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Header */}
      <header className="mb-8 text-center">
        <div className="flex items-center justify-center gap-3 mb-3">
          <div className="p-2 bg-brand-600 rounded-xl">
            <Sparkles className="w-6 h-6 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-gray-900">GarimpoGov</h1>
        </div>
        <p className="text-gray-600 max-w-xl mx-auto">
          Monitore editais de concursos publicos com inteligencia artificial.
          Busque, filtre e converse diretamente com os editais.
        </p>
      </header>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 mb-4 text-sm">
          {error}
        </div>
      )}

      <FiltersPanel onFilter={handleFilter} loading={loading} />
      <ConcursoList
        data={data}
        loading={loading}
        onChat={handleChat}
        onPageChange={handlePageChange}
      />

      <ChatModal
        concurso={selectedConcurso}
        open={chatOpen}
        onClose={() => setChatOpen(false)}
      />
    </div>
  )
}
