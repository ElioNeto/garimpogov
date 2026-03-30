import { useState } from 'react'
import { Search, SlidersHorizontal } from 'lucide-react'
import type { ConcursoFilters } from '../services/api'

interface FiltersPanelProps {
  onFilter: (filters: ConcursoFilters) => void
  loading: boolean
}

export default function FiltersPanel({ onFilter, loading }: FiltersPanelProps) {
  const [orgao, setOrgao] = useState('')
  const [status, setStatus] = useState('')
  const [salarioMin, setSalarioMin] = useState('')
  const [salarioMax, setSalarioMax] = useState('')

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    onFilter({
      orgao: orgao || undefined,
      status: status || undefined,
      salario_min: salarioMin ? Number(salarioMin) : undefined,
      salario_max: salarioMax ? Number(salarioMax) : undefined,
      page: 1,
    })
  }

  function handleReset() {
    setOrgao('')
    setStatus('')
    setSalarioMin('')
    setSalarioMax('')
    onFilter({ page: 1 })
  }

  return (
    <div className="card p-4 mb-6">
      <div className="flex items-center gap-2 mb-4">
        <SlidersHorizontal className="w-5 h-5 text-brand-600" />
        <h2 className="font-semibold text-gray-800">Filtros</h2>
      </div>

      <form onSubmit={handleSubmit} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Orgao / Instituicao</label>
          <input
            type="text"
            className="input-field"
            placeholder="Ex: Policia Federal"
            value={orgao}
            onChange={(e) => setOrgao(e.target.value)}
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Status</label>
          <select
            className="input-field"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
          >
            <option value="">Todos</option>
            <option value="aberto">Aberto</option>
            <option value="encerrado">Encerrado</option>
            <option value="suspenso">Suspenso</option>
          </select>
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Salario Minimo (R$)</label>
          <input
            type="number"
            className="input-field"
            placeholder="Ex: 3000"
            value={salarioMin}
            onChange={(e) => setSalarioMin(e.target.value)}
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Salario Maximo (R$)</label>
          <input
            type="number"
            className="input-field"
            placeholder="Ex: 15000"
            value={salarioMax}
            onChange={(e) => setSalarioMax(e.target.value)}
          />
        </div>

        <div className="sm:col-span-2 lg:col-span-4 flex gap-2 justify-end">
          <button type="button" onClick={handleReset} className="btn-secondary text-sm">
            Limpar
          </button>
          <button type="submit" disabled={loading} className="btn-primary text-sm flex items-center gap-2">
            <Search className="w-4 h-4" />
            {loading ? 'Buscando...' : 'Buscar'}
          </button>
        </div>
      </form>
    </div>
  )
}
