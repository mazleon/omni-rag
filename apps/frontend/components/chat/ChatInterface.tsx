'use client';

import { useEffect, useRef } from 'react';
import { MessageSquare, Trash2, Loader2 } from 'lucide-react';
import { useChat } from '@/hooks/useChat';
import { MessageBubble } from './MessageBubble';
import { ChatInput } from './ChatInput';
import { Button } from '@/components/ui/Button';

interface ChatInterfaceProps {
  collectionId?: string;
}

export function ChatInterface({ collectionId }: ChatInterfaceProps) {
  const { messages, isLoading, error, sendMessage, submitFeedback, clearMessages } =
    useChat(collectionId);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="flex h-full flex-col bg-zinc-950">
      {messages.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center px-4">
          <div className="mb-6 flex h-12 w-12 items-center justify-center rounded-xl bg-zinc-800">
            <MessageSquare className="h-6 w-6 text-zinc-400" />
          </div>
          <h2 className="mb-2 text-lg font-medium text-zinc-100">
            How can I help you today?
          </h2>
          <p className="max-w-sm text-center text-sm text-zinc-500 mb-8">
            Ask questions about your documents and get accurate, citation-backed answers.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-lg">
            {[
              { icon: '📄', label: 'Summarize documents', query: 'Summarize the key points from my uploaded documents' },
              { icon: '🔍', label: 'Find information', query: 'What are the main findings in my documents?' },
              { icon: '📊', label: 'Compare documents', query: 'Compare the content across my uploaded documents' },
              { icon: '💡', label: 'Extract insights', query: 'What are the key insights from my documents?' },
            ].map((suggestion) => (
              <button
                key={suggestion.label}
                onClick={() => sendMessage(suggestion.query)}
                className="flex items-center gap-2.5 rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2.5 text-left transition-colors hover:border-zinc-700 hover:bg-zinc-800/50"
              >
                <span className="text-base">{suggestion.icon}</span>
                <span className="text-xs text-zinc-400">
                  {suggestion.label}
                </span>
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div className="flex-1 overflow-auto">
          <div className="mx-auto max-w-3xl px-4 py-6 space-y-6">
            {messages.map((msg) => (
              <MessageBubble
                key={msg.id}
                message={msg}
                onFeedback={submitFeedback}
              />
            ))}
            {error && !isLoading && (
              <div className="flex items-center justify-center gap-2 rounded-lg border border-red-500/20 bg-red-500/5 px-4 py-2.5">
                <span className="text-sm text-red-400">{error}</span>
              </div>
            )}
            {isLoading && (
              <div className="flex items-center gap-2 text-zinc-500">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span className="text-sm">Thinking...</span>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        </div>
      )}

      <div className="border-t border-zinc-800 bg-zinc-950">
        <div className="mx-auto max-w-3xl px-4 py-3">
          <ChatInput onSend={sendMessage} disabled={isLoading} />
          {messages.length > 0 && (
            <div className="flex items-center justify-between mt-2 px-1">
              <p className="text-[10px] text-zinc-600">
                OmniRAG may produce inaccurate information. Verify important details.
              </p>
              <Button
                variant="ghost"
                size="sm"
                onClick={clearMessages}
                className="text-zinc-600 hover:text-zinc-400 text-xs h-6 px-2"
              >
                <Trash2 className="h-3 w-3 mr-1" />
                Clear
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
