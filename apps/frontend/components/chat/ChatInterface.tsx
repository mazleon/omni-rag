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
    <div className="flex h-full flex-col">
      {/* Toolbar */}
      {messages.length > 0 && (
        <div className="flex items-center justify-between border-b border-slate-800 px-4 py-2">
          <p className="text-xs text-slate-500">
            {messages.length} message{messages.length !== 1 ? 's' : ''}
          </p>
          <div className="flex items-center gap-2">
            {isLoading && (
              <div className="flex items-center gap-1 text-xs text-slate-500">
                <Loader2 className="h-3 w-3 animate-spin" />
                Thinking...
              </div>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={clearMessages}
              className="text-slate-500 hover:text-slate-300"
            >
              <Trash2 className="h-3.5 w-3.5" />
              Clear
            </Button>
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-auto px-6 py-4">
        {messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-600/10">
              <MessageSquare className="h-7 w-7 text-blue-400" />
            </div>
            <h2 className="mb-1 text-lg font-semibold text-white">
              Ask anything about your documents
            </h2>
            <p className="max-w-sm text-sm text-slate-500">
              Upload PDFs, spreadsheets, or presentations — then ask questions
              and get grounded, citation-backed answers.
            </p>
          </div>
        ) : (
          <div className="space-y-5">
            {messages.map((msg) => (
              <MessageBubble
                key={msg.id}
                message={msg}
                onFeedback={submitFeedback}
              />
            ))}
            {error && !isLoading && (
              <div className="text-center">
                <p className="text-xs text-red-400 mb-2">{error}</p>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      <ChatInput
        onSend={sendMessage}
        disabled={isLoading}
      />
    </div>
  );
}
