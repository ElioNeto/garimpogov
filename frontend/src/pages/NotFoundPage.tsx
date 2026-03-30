import { Link } from 'react-router-dom'
import { Home } from 'lucide-react'

export default function NotFoundPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen text-center px-4">
      <h1 className="text-6xl font-bold text-brand-600 mb-4">404</h1>
      <p className="text-xl text-gray-700 mb-2">Pagina nao encontrada</p>
      <p className="text-gray-500 mb-8">A pagina que voce esta procurando nao existe.</p>
      <Link to="/" className="btn-primary flex items-center gap-2">
        <Home className="w-4 h-4" />
        Voltar ao Inicio
      </Link>
    </div>
  )
}
