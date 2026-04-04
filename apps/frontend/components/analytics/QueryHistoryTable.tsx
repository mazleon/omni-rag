'use client';

import { useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { useQueryHistory } from '@/hooks/useAnalytics';
import { Skeleton } from '@/components/ui/Skeleton';
import { Button } from '@/components/ui/Button';
import { formatDateTime, formatLatency, truncate } from '@/lib/utils';

const PAGE_SIZE = 10;

export function QueryHistoryTable() {
  const [offset, setOffset] = useState(0);
  const { data, isLoading } = useQueryHistory(PAGE_SIZE, offset);

  const total = data?.total ?? 0;
  const page = Math.floor(offset / PAGE_SIZE) + 1;
  const totalPages = Math.ceil(total / PAGE_SIZE);

  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-10 w-full" />
        ))}
      </div>
    );
  }

  if (!data || data.queries.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-slate-500">
        No queries recorded yet.
      </p>
    );
  }

  return (
    <div>
      <div className="overflow-hidden rounded-xl border border-slate-800">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-800 bg-slate-900">
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-400">Query</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-400">Latency</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-400">Tokens</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-400">Cost</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-400">Time</th>
            </tr>
          </thead>
          <tbody>
            {data.queries.map((q) => (
              <tr key={q.id} className="border-b border-slate-800 hover:bg-slate-800/30">
                <td className="max-w-[300px] px-4 py-3 text-white">
                  {truncate(q.query_text, 60)}
                </td>
                <td className="px-4 py-3 text-slate-400">{formatLatency(q.latency_ms)}</td>
                <td className="px-4 py-3 text-slate-400">
                  {q.tokens_used?.toLocaleString() ?? '—'}
                </td>
                <td className="px-4 py-3 text-slate-400">
                  {q.cost_usd !== null ? `$${q.cost_usd.toFixed(4)}` : '—'}
                </td>
                <td className="px-4 py-3 text-slate-400 whitespace-nowrap">
                  {formatDateTime(q.created_at)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="mt-3 flex items-center justify-between text-xs text-slate-400">
          <span>
            Page {page} of {totalPages} ({total} total)
          </span>
          <div className="flex gap-2">
            <Button
              variant="secondary"
              size="icon"
              onClick={() => setOffset((o) => o - PAGE_SIZE)}
              disabled={offset === 0}
              aria-label="Previous"
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <Button
              variant="secondary"
              size="icon"
              onClick={() => setOffset((o) => o + PAGE_SIZE)}
              disabled={offset + PAGE_SIZE >= total}
              aria-label="Next"
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
