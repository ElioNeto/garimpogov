import { FileSearch } from 'lucide-react'
import ConcursoCard from './ConcursoCard'
import type { Concurso, PaginatedConcursos } from '../services/api'

interface ConcursoListProps {
  data: PaginatedConcursos | null
  loading: boolean
  onChat: (concurso: Concurso) => void
  onPageChange: (page: number) => void
}

export default function ConcursoList({ data, loading, onChat, onPageChange }: ConcursoListProps) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="card p-5 animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-3/4 mb-3"></div>
            <div className="h-3 bg-gray-200 rounded w-1/2 mb-2"></div>
            <div className="h-3 bg-gray-200 rounded w-2/3"></div>
          </div>
        ))}
      </div>
    )
  }

  if (!data || data.items.length === 0) {
    return (
      <div className="text-center py-16 text-gray-500">
        <FileSearch className="w-12 h-12 mx-auto mb-3 opacity-40" />
        <p className="font-medium">Nenhum concurso encontrado</p>
        <p className="text-sm mt-1">Tente ajustar os filtros</p>
      </div>
    )
  }

  const totalPages = Math.ceil(data.total / data.page_size)

  return (
    <div>
      <p className="text-sm text-gray-500 mb-4">
        {data.total} concurso{data.total !== 1 ? 's' : ''} encontrado{data.total !== 1 ? 's' : ''}
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {data.items.map((concurso) => (
          <ConcursoCard key={concurso.id} concurso={concurso} onChat={onChat} />
        ))}
      </div>

      {totalPages > 1 && (
        <div className="flex justify-center gap-2 mt-8">
          <button
            onClick={() => onPageChange(data.page - 1)}
            disabled={data.page <= 1}
            className="btn-secondary text-sm disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Anterior
          </button>
          <span className="px-4 py-2 text-sm text-gray-600">
            Pagina {data.page} de {totalPages}
          </span>
          <button
            onClick={() => onPageChange(data.page + 1)}
            disabled={data.page >= totalPages}
            className="btn-secondary text-sm disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Proxima
          </button>
        </div>
      )}
    </div>
  )
}
