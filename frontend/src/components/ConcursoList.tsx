import ConcursoCard from './ConcursoCard'
import type { Concurso } from '../services/api'

interface ConcursoListProps {
  concursos: Concurso[]
  total: number
  page: number
  pageSize: number
  totalPages: number
  loading: boolean
  onChat: (concurso: Concurso) => void
  onPageChange: (page: number) => void
}

export default function ConcursoList({
  concursos,
  total,
  page,
  pageSize,
  totalPages,
  loading,
  onChat,
  onPageChange,
}: ConcursoListProps) {
  if (loading) {
    return (
      <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="card animate-pulse">
            <div className="h-5 bg-gray-200 rounded w-3/4 mb-3" />
            <div className="h-4 bg-gray-200 rounded w-1/2 mb-2" />
            <div className="h-4 bg-gray-200 rounded w-1/3" />
          </div>
        ))}
      </div>
    )
  }

  if (!loading && concursos.length === 0) {
    return (
      <div className="mt-12 text-center text-gray-500">
        <p className="text-lg font-medium">Nenhum concurso encontrado.</p>
        <p className="text-sm mt-1">Tente ajustar os filtros.</p>
      </div>
    )
  }

  return (
    <div className="mt-6">
      <p className="text-sm text-gray-500 mb-4">
        {total} concurso{total !== 1 ? 's' : ''} encontrado{total !== 1 ? 's' : ''}
        {totalPages > 1 && ` — página ${page} de ${totalPages}`}
      </p>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {concursos.map((c) => (
          <ConcursoCard key={c.id} concurso={c} onChat={onChat} />
        ))}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="mt-8 flex items-center justify-center gap-2">
          <button
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1}
            className="px-4 py-2 rounded-lg border border-gray-300 text-sm font-medium disabled:opacity-40 hover:bg-gray-50 transition-colors"
          >
            Anterior
          </button>
          <span className="px-4 py-2 text-sm text-gray-600">
            {page} / {totalPages}
          </span>
          <button
            onClick={() => onPageChange(page + 1)}
            disabled={page >= totalPages}
            className="px-4 py-2 rounded-lg border border-gray-300 text-sm font-medium disabled:opacity-40 hover:bg-gray-50 transition-colors"
          >
            Próxima
          </button>
        </div>
      )}
    </div>
  )
}
