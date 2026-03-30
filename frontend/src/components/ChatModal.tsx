import { useEffect, useRef, useState } from 'react'
import * as Dialog from '@radix-ui/react-dialog'
import { Send, X } from 'lucide-react'
import ChatMessage, { type Message } from './ChatMessage'
import { streamChat } from '../services/api'
import type { Concurso } from '../services/api'

interface ChatModalProps {
  concurso: Concurso | null
  open: boolean
  onClose: () => void
}

export default function ChatModal({ concurso, open, onClose }: ChatModalProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const abortRef = useRef<(() => void) | null>(null)

  useEffect(() => {
    if (open && concurso) {
      setMessages([
        {
          id: 'welcome',
          role: 'assistant',
          content: `Ola! Posso responder perguntas sobre o edital de **${concurso.instituicao}**. O que voce gostaria de saber?`,
        },
      ])
    }
  }, [open, concurso])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  function handleClose() {
    if (abortRef.current) {
      abortRef.current()
      abortRef.current = null
    }
    setIsStreaming(false)
    setMessages([])
    setInput('')
    onClose()
  }

  async function handleSend() {
    if (!input.trim() || isStreaming || !concurso) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
    }

    const assistantId = (Date.now() + 1).toString()
    const assistantMessage: Message = {
      id: assistantId,
      role: 'assistant',
      content: '',
      streaming: true,
    }

    setMessages((prev) => [...prev, userMessage, assistantMessage])
    setInput('')
    setIsStreaming(true)

    const question = userMessage.content

    const abort = streamChat(
      concurso.id,
      question,
      (chunk) => {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId ? { ...m, content: m.content + chunk } : m
          )
        )
      },
      () => {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId ? { ...m, streaming: false } : m
          )
        )
        setIsStreaming(false)
        abortRef.current = null
      },
      (error) => {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, content: `Erro: ${error}`, streaming: false }
              : m
          )
        )
        setIsStreaming(false)
        abortRef.current = null
      }
    )

    abortRef.current = abort
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <Dialog.Root open={open} onOpenChange={(o) => !o && handleClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/50 z-40 backdrop-blur-sm" />
        <Dialog.Content className="fixed inset-0 sm:inset-auto sm:top-1/2 sm:left-1/2 sm:-translate-x-1/2 sm:-translate-y-1/2 sm:w-full sm:max-w-2xl sm:h-[85vh] z-50 bg-white sm:rounded-2xl flex flex-col overflow-hidden shadow-2xl">
          {/* Header */}
          <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200 bg-white">
            <div>
              <Dialog.Title className="font-semibold text-gray-900">
                Chat com o Edital
              </Dialog.Title>
              {concurso && (
                <p className="text-xs text-gray-500 mt-0.5 truncate max-w-xs">
                  {concurso.instituicao}
                </p>
              )}
            </div>
            <Dialog.Close asChild>
              <button
                onClick={handleClose}
                className="p-2 rounded-lg hover:bg-gray-100 text-gray-500 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </Dialog.Close>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} />
            ))}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="p-4 border-t border-gray-200 bg-white">
            <div className="flex gap-2">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Digite sua pergunta sobre o edital..."
                rows={2}
                disabled={isStreaming}
                className="flex-1 input-field resize-none disabled:opacity-60"
              />
              <button
                onClick={handleSend}
                disabled={!input.trim() || isStreaming}
                className="btn-primary self-end disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
            <p className="text-xs text-gray-400 mt-1.5">Enter para enviar &bull; Shift+Enter para nova linha</p>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
