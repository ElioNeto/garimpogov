import { Building2, Calendar, DollarSign, ExternalLink, MessageCircle } from 'lucide-react'
import type { Concurso } from '../services/api'

interface ConcursoCardProps {
  concurso: Concurso
  onChat: (concurso: Concurso) => void
}

const STATUS_COLORS: Record<string, string> = {
  aberto: 'bg-green-100 text-green-800',
  encerrado: 'bg-red-100 text-red-800',
  suspenso: 'bg-yellow-100 text-yellow-800',
}

function formatSalary(value: number | null): string {
  if (!value) return 'N/A'
  return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return 'N/A'
  return new Date(dateStr).toLocaleDateString('pt-BR')
}

export default function ConcursoCard({ concurso, onChat }: ConcursoCardProps) {
  const statusClass = STATUS_COLORS[concurso.status] || 'bg-gray-100 text-gray-800'

  return (
    <div className="card p-5 flex flex-col gap-3">
      <div className="flex items-start justify-between gap-2">
        <h3 className="font-semibold text-gray-900 text-base leading-tight">
          {concurso.instituicao}
        </h3>
        <span className={`text-xs px-2 py-1 rounded-full font-medium whitespace-nowrap ${statusClass}`}>
          {concurso.status}
        </span>
      </div>

      {concurso.orgao && (
        <div className="flex items-center gap-2 text-sm text-gray-600">
          <Building2 className="w-4 h-4 flex-shrink-0" />
          <span>{concurso.orgao}</span>
        </div>
      )}

      <div className="flex flex-wrap gap-4 text-sm text-gray-600">
        <div className="flex items-center gap-1.5">
          <DollarSign className="w-4 h-4 text-green-600" />
          <span>Ate {formatSalary(concurso.salario_maximo)}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <Calendar className="w-4 h-4 text-orange-500" />
          <span>Encerra: {formatDate(concurso.data_encerramento)}</span>
        </div>
      </div>

      <div className="flex gap-2 mt-auto pt-2 border-t border-gray-100">
        <button
          onClick={() => onChat(concurso)}
          className="btn-primary text-xs flex items-center gap-1.5 flex-1 justify-center"
        >
          <MessageCircle className="w-3.5 h-3.5" />
          Perguntar ao Edital
        </button>
        <a
          href={concurso.link_edital}
          target="_blank"
          rel="noopener noreferrer"
          className="btn-secondary text-xs flex items-center gap-1.5"
        >
          <ExternalLink className="w-3.5 h-3.5" />
          Edital
        </a>
      </div>
    </div>
  )
}
