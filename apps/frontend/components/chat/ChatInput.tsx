'use client';

import { useState, KeyboardEvent, useRef, useEffect } from 'react';
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
  placeholder = 'Ask anything...',
}: ChatInputProps) {
  const [internalValue, setInternalValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const value = externalValue ?? internalValue;
  const onChange = externalOnChange ?? ((e) => setInternalValue(e.target.value));

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`;
    }
  }, [value]);

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
    <div className="relative">
      <div className={cn(
        'flex items-end gap-2 rounded-lg border bg-zinc-900 px-3 py-2 transition-colors',
        'border-zinc-800 focus-within:border-zinc-700',
      )}>
        <textarea
          ref={textareaRef}
          value={value}
          onChange={onChange}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          rows={1}
          className={cn(
            'flex-1 resize-none bg-transparent py-1 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none',
            'max-h-40 min-h-[24px] leading-relaxed',
            disabled && 'opacity-50',
          )}
        />
        <button
          onClick={handleSend}
          disabled={disabled || !value.trim()}
          className={cn(
            'shrink-0 rounded-md p-2 transition-colors',
            disabled || !value.trim()
              ? 'text-zinc-600 cursor-not-allowed'
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
    </div>
  );
}
