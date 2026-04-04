'use client';

import { useState, KeyboardEvent } from 'react';
import { Send, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ChatInputProps {
  value?: string;
  onChange?: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export function ChatInput({
  value: externalValue,
  onChange: externalOnChange,
  onSend,
  disabled = false,
  placeholder = 'Ask a question about your documents...',
}: ChatInputProps) {
  const [internalValue, setInternalValue] = useState('');

  const value = externalValue ?? internalValue;
  const onChange = externalOnChange ?? ((e) => setInternalValue(e.target.value));

  const handleSend = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    if (!externalValue) {
      setInternalValue('');
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="border-t border-slate-800 p-4">
      <div className="flex items-end gap-2 rounded-xl border border-slate-700 bg-slate-800/50 px-3 py-2 focus-within:border-blue-500 focus-within:outline-none">
        <textarea
          value={value}
          onChange={onChange}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          rows={1}
          className={cn(
            'flex-1 resize-none bg-transparent py-1.5 text-sm text-white placeholder-slate-500 focus:outline-none',
            'max-h-32 min-h-[24px]',
            disabled && 'opacity-50',
          )}
          style={{
            height: 'auto',
            minHeight: '24px',
            maxHeight: '128px',
          }}
          onInput={(e) => {
            const target = e.target as HTMLTextAreaElement;
            target.style.height = 'auto';
            target.style.height = `${Math.min(target.scrollHeight, 128)}px`;
          }}
        />
        <button
          onClick={handleSend}
          disabled={disabled || !value.trim()}
          className={cn(
            'shrink-0 rounded-lg p-2 transition-colors',
            disabled || !value.trim()
              ? 'text-slate-600'
              : 'bg-blue-600 text-white hover:bg-blue-500',
          )}
          aria-label="Send message"
        >
          {disabled ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
        </button>
      </div>
      <p className="mt-2 text-center text-xs text-slate-600">
        OmniRAG may produce inaccurate information. Verify important details.
      </p>
    </div>
  );
}
