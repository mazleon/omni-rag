'use client';

import { useCallback, useRef, useState } from 'react';
import { queryApi, feedbackApi } from '@/lib/api';
import type { QuerySource } from '@/types/api';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: QuerySource[];
  queryId?: string;
  isStreaming?: boolean;
  timestamp: Date;
}

export function useChat(collectionId?: string) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<boolean>(false);

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || isLoading) return;

      setError(null);
      abortRef.current = false;

      const userMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'user',
        content: text,
        timestamp: new Date(),
      };

      const assistantId = crypto.randomUUID();
      const assistantMsg: ChatMessage = {
        id: assistantId,
        role: 'assistant',
        content: '',
        isStreaming: true,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setIsLoading(true);

      try {
        await queryApi.stream(
          text,
          (chunk) => {
            if (abortRef.current) return;
            if (chunk.type === 'content' && chunk.content) {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? { ...m, content: m.content + chunk.content }
                    : m,
                ),
              );
            } else if (chunk.type === 'sources' && chunk.sources) {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? { ...m, sources: chunk.sources, queryId: chunk.query_id }
                    : m,
                ),
              );
            } else if (chunk.type === 'end') {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId ? { ...m, isStreaming: false } : m,
                ),
              );
            } else if (chunk.type === 'error') {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? {
                        ...m,
                        content: chunk.error ?? 'An error occurred',
                        isStreaming: false,
                      }
                    : m,
                ),
              );
            }
          },
          collectionId,
        );
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Failed to get response';
        setError(msg);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, content: msg, isStreaming: false }
              : m,
          ),
        );
      } finally {
        setIsLoading(false);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId ? { ...m, isStreaming: false } : m,
          ),
        );
      }
    },
    [isLoading, collectionId],
  );

  const submitFeedback = useCallback(
    async (queryId: string, value: -1 | 0 | 1) => {
      await feedbackApi.submit({ query_id: queryId, feedback: value });
    },
    [],
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return { messages, isLoading, error, sendMessage, submitFeedback, clearMessages };
}
