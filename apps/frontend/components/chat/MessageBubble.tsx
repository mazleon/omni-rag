'use client';

import { useState } from 'react';
import { ThumbsUp, ThumbsDown, ChevronDown, ChevronUp, Copy, Check } from 'lucide-react';
import { cn, formatDateTime } from '@/lib/utils';
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
      // Fallback for older browsers
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
    <div className={cn('flex', isUser ? 'justify-end' : 'justify-start')}>
      <div className={cn('max-w-[78%] space-y-2', isUser ? 'items-end' : 'items-start')}>
        <div
          className={cn(
            'group relative rounded-2xl px-4 py-3 text-sm leading-relaxed',
            isUser
              ? 'rounded-tr-sm bg-blue-600 text-white'
              : 'rounded-tl-sm bg-slate-800 text-slate-100',
          )}
        >
          {/* Copy button (assistant only) */}
          {!isUser && (
            <button
              onClick={handleCopy}
              className="absolute right-2 top-2 rounded p-1 text-slate-500 opacity-0 transition-opacity hover:text-slate-300 group-hover:opacity-100"
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
              <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-slate-400" />
            </span>
          ) : (
            <span className="whitespace-pre-wrap">{message.content}</span>
          )}
        </div>

        {/* Sources + feedback (assistant only) */}
        {!isUser && !message.isStreaming && (
          <div className="space-y-1.5 px-1">
            {message.sources && message.sources.length > 0 && (
              <div>
                <button
                  onClick={() => setShowSources((v) => !v)}
                  className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-300"
                >
                  {showSources ? (
                    <ChevronUp className="h-3 w-3" />
                  ) : (
                    <ChevronDown className="h-3 w-3" />
                  )}
                  {message.sources.length} source
                  {message.sources.length !== 1 ? 's' : ''}
                </button>
                {showSources && (
                  <div className="mt-2 space-y-2">
                    {message.sources.map((src, i) => (
                      <SourceCard key={src.chunk_id} source={src} index={i} />
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Feedback */}
            {message.queryId && (
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-600">Helpful?</span>
                <button
                  onClick={() => handleFeedback(1)}
                  disabled={feedbackGiven !== null}
                  className={cn(
                    'rounded p-1 text-slate-500 transition-colors hover:text-emerald-400',
                    feedbackGiven === 1 && 'text-emerald-400',
                  )}
                  aria-label="Thumbs up"
                >
                  <ThumbsUp className="h-3.5 w-3.5" />
                </button>
                <button
                  onClick={() => handleFeedback(-1)}
                  disabled={feedbackGiven !== null}
                  className={cn(
                    'rounded p-1 text-slate-500 transition-colors hover:text-red-400',
                    feedbackGiven === -1 && 'text-red-400',
                  )}
                  aria-label="Thumbs down"
                >
                  <ThumbsDown className="h-3.5 w-3.5" />
                </button>
              </div>
            )}
          </div>
        )}

        <p className={cn('px-1 text-xs text-slate-600', isUser && 'text-right')}>
          {formatDateTime(message.timestamp.toISOString())}
        </p>
      </div>
    </div>
  );
}
