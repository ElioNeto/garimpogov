import { useState } from 'react'
import { Sparkles } from 'lucide-react'
import FiltersPanel from '../components/FiltersPanel'
import ConcursoList from '../components/ConcursoList'
import ChatModal from '../components/ChatModal'
import type { Concurso, ConcursoFilters } from '../services/api'
import { useConcursos } from '../hooks/useConcursos'

export default function HomePage() {
  const [filters, setFilters] = useState<ConcursoFilters>({})
  const [selectedConcurso, setSelectedConcurso] = useState<Concurso | null>(null)
  const [chatOpen, setChatOpen] = useState(false)

  const {
    concursos,
    total,
    page,
    pageSize,
    totalPages,
    loading,
    error,
    goToPage,
  } = useConcursos(filters)

  function handleFilter(newFilters: ConcursoFilters) {
    setFilters(newFilters)
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
          Monitore editais de concursos públicos com inteligência artificial.
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
        concursos={concursos}
        total={total}
        page={page}
        pageSize={pageSize}
        totalPages={totalPages}
        loading={loading}
        onChat={handleChat}
        onPageChange={goToPage}
      />

      <ChatModal
        concurso={selectedConcurso}
        open={chatOpen}
        onClose={() => setChatOpen(false)}
      />
    </div>
  )
}
