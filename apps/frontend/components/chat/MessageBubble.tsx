'use client';

import { useState } from 'react';
import { ThumbsUp, ThumbsDown, ChevronDown, ChevronUp, Copy, Check } from 'lucide-react';
import { cn } from '@/lib/utils';
import { SourceCard } from './SourceCard';
import type { ChatMessage } from '@/hooks/useChat';

interface MessageBubbleProps {
  message: ChatMessage;
  onFeedback?: (queryId: string, value: -1 | 1) => void;
}

export function MessageBubble({ message, onFeedback }: MessageBubbleProps) {
  const [showSources, setShowSources] = useState(false);
  const [feedbackGiven, setFeedbackGiven] = useState<-1 | 1 | null>(null);
  const [copied, setCopied] = useState(false);

  const isUser = message.role === 'user';

  const handleFeedback = (value: -1 | 1) => {
    if (!message.queryId || feedbackGiven !== null) return;
    setFeedbackGiven(value);
    onFeedback?.(message.queryId, value);
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      const textarea = document.createElement('textarea');
      textarea.value = message.content;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className={cn('flex gap-3', isUser ? 'justify-end' : 'justify-start')}>
      {!isUser && (
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-zinc-800 text-[10px] font-medium text-zinc-400 mt-0.5">
          AI
        </div>
      )}

      <div className={cn('max-w-[80%]', isUser ? 'items-end' : 'items-start')}>
        <div
          className={cn(
            'group relative rounded-lg px-3.5 py-2.5 text-sm leading-relaxed',
            isUser
              ? 'bg-blue-600 text-white'
              : 'bg-zinc-800/50 text-zinc-200',
          )}
        >
          {!isUser && (
            <button
              onClick={handleCopy}
              className="absolute right-1.5 top-1.5 rounded p-1 text-zinc-500 opacity-0 transition-opacity hover:text-zinc-300 group-hover:opacity-100"
              aria-label="Copy message"
            >
              {copied ? (
                <Check className="h-3.5 w-3.5 text-emerald-400" />
              ) : (
                <Copy className="h-3.5 w-3.5" />
              )}
            </button>
          )}

          {message.isStreaming ? (
            <span>
              {message.content}
              <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-zinc-400" />
            </span>
          ) : (
            <span className="whitespace-pre-wrap">{message.content}</span>
          )}
        </div>

        {!isUser && !message.isStreaming && (
          <div className="space-y-1.5 mt-1.5">
            {message.sources && message.sources.length > 0 && (
              <div>
                <button
                  onClick={() => setShowSources((v) => !v)}
                  className="flex items-center gap-1 rounded px-1.5 py-1 text-xs text-zinc-500 hover:text-zinc-300"
                >
                  {showSources ? (
                    <ChevronUp className="h-3 w-3" />
                  ) : (
                    <ChevronDown className="h-3 w-3" />
                  )}
                  {message.sources.length} source{message.sources.length !== 1 ? 's' : ''}
                </button>
                {showSources && (
                  <div className="mt-1.5 space-y-1.5">
                    {message.sources.map((src, i) => (
                      <SourceCard key={src.chunk_id} source={src} index={i} />
                    ))}
                  </div>
                )}
              </div>
            )}

            {message.queryId && (
              <div className="flex items-center gap-1 px-1">
                <span className="text-[10px] text-zinc-600">Helpful?</span>
                <button
                  onClick={() => handleFeedback(1)}
                  disabled={feedbackGiven !== null}
                  className={cn(
                    'rounded p-1 transition-colors',
                    feedbackGiven === 1
                      ? 'text-emerald-400'
                      : 'text-zinc-600 hover:text-emerald-400',
                  )}
                  aria-label="Thumbs up"
                >
                  <ThumbsUp className="h-3 w-3" />
                </button>
                <button
                  onClick={() => handleFeedback(-1)}
                  disabled={feedbackGiven !== null}
                  className={cn(
                    'rounded p-1 transition-colors',
                    feedbackGiven === -1
                      ? 'text-red-400'
                      : 'text-zinc-600 hover:text-red-400',
                  )}
                  aria-label="Thumbs down"
                >
                  <ThumbsDown className="h-3 w-3" />
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {isUser && (
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-zinc-700 text-[10px] font-medium text-zinc-300 mt-0.5">
          {message.content?.[0]?.toUpperCase() ?? 'U'}
        </div>
      )}
    </div>
  );
}
