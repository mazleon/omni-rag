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
    <div className="rounded-lg border border-slate-700 bg-slate-800/50 p-3">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-start justify-between gap-2 text-left"
      >
        <div className="flex items-center gap-2 min-w-0">
          <span className="shrink-0 flex h-5 w-5 items-center justify-center rounded-full bg-blue-600/20 text-xs font-semibold text-blue-400">
            {index + 1}
          </span>
          <FileText className="h-3.5 w-3.5 shrink-0 text-slate-400" />
          <span className="truncate text-xs font-medium text-slate-300">
            {docLabel}
            {pages ? ` · p.${pages.join(', ')}` : ''}
          </span>
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          {score > 0 && (
            <span className="text-xs text-slate-500">
              {(score * 100).toFixed(0)}%
            </span>
          )}
          {expanded ? (
            <ChevronUp className="h-3.5 w-3.5 text-slate-500" />
          ) : (
            <ChevronDown className="h-3.5 w-3.5 text-slate-500" />
          )}
        </div>
      </button>
      {expanded && source.content && (
        <p className="mt-2 border-t border-slate-700 pt-2 text-xs leading-relaxed text-slate-400">
          {source.content}
        </p>
      )}
      {!expanded && source.content && (
        <p className="mt-1 text-xs text-slate-500">
          {truncate(source.content, 120)}
        </p>
      )}
    </div>
  );
}
