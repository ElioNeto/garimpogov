import { useState, useRef, useCallback } from 'react';
import { streamChat } from '../services/api';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  loading?: boolean;
}

export function useChat(concursoId: string) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const abortRef = useRef<(() => void) | null>(null);

  const sendMessage = useCallback(async (question: string) => {
    if (!question.trim() || isStreaming) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: question.trim(),
    };

    const assistantMsgId = `assistant-${Date.now()}`;
    const assistantMsg: ChatMessage = {
      id: assistantMsgId,
      role: 'assistant',
      content: '',
      loading: true,
    };

    setMessages(prev => [...prev, userMsg, assistantMsg]);
    setIsStreaming(true);

    let accumulated = '';

    const abort = streamChat(
      concursoId,
      question.trim(),
      (chunk: string) => {
        accumulated += chunk;
        setMessages(prev =>
          prev.map(m =>
            m.id === assistantMsgId
              ? { ...m, content: accumulated, loading: false }
              : m
          )
        );
      },
      () => {
        setMessages(prev =>
          prev.map(m =>
            m.id === assistantMsgId ? { ...m, loading: false } : m
          )
        );
        setIsStreaming(false);
      },
      (err: string) => {
        setMessages(prev =>
          prev.map(m =>
            m.id === assistantMsgId
              ? { ...m, content: `Erro: ${err}`, loading: false }
              : m
          )
        );
        setIsStreaming(false);
      }
    );

    abortRef.current = abort;
  }, [concursoId, isStreaming]);

  const clearMessages = useCallback(() => {
    if (abortRef.current) abortRef.current();
    setMessages([]);
    setIsStreaming(false);
  }, []);

  const stopStreaming = useCallback(() => {
    if (abortRef.current) abortRef.current();
    setIsStreaming(false);
  }, []);

  return { messages, isStreaming, sendMessage, clearMessages, stopStreaming };
}
