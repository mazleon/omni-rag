'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp, FileText } from 'lucide-react';
import { cn, truncate } from '@/lib/utils';
import type { QuerySource } from '@/types/api';

interface SourceCardProps {
  source: QuerySource;
  index: number;
}

export function SourceCard({ source, index }: SourceCardProps) {
  const [expanded, setExpanded] = useState(false);

  const docLabel = source.filename
    ? source.filename
    : source.document_id
      ? `Document ${source.document_id.slice(0, 8)}`
      : `Source ${index + 1}`;

  const score = typeof source.score === 'number' ? source.score : 0;
  const pages = source.page_numbers && source.page_numbers.length > 0
    ? source.page_numbers
    : null;

  return (
    <div className="rounded-md border border-zinc-800 bg-zinc-900/50">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-start justify-between gap-2 px-2.5 py-2 text-left"
      >
        <div className="flex items-center gap-2 min-w-0">
          <span className="shrink-0 flex h-5 w-5 items-center justify-center rounded bg-zinc-800 text-[10px] font-medium text-zinc-400">
            {index + 1}
          </span>
          <FileText className="h-3.5 w-3.5 shrink-0 text-zinc-500" />
          <span className="truncate text-xs font-medium text-zinc-300">
            {docLabel}
            {pages ? ` · p.${pages.join(', ')}` : ''}
          </span>
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          {score > 0 && (
            <span className="text-[10px] text-zinc-500">
              {(score * 100).toFixed(0)}%
            </span>
          )}
          {expanded ? (
            <ChevronUp className="h-3 w-3 text-zinc-500" />
          ) : (
            <ChevronDown className="h-3 w-3 text-zinc-500" />
          )}
        </div>
      </button>
      {expanded && source.content && (
        <p className="border-t border-zinc-800 px-2.5 py-2 text-xs leading-relaxed text-zinc-400">
          {source.content}
        </p>
      )}
      {!expanded && source.content && (
        <p className="px-2.5 pb-2 text-[10px] text-zinc-600">
          {truncate(source.content, 100)}
        </p>
      )}
    </div>
  );
}
