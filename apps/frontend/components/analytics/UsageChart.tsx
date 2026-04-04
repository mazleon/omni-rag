'use client';

import { useMemo } from 'react';
import type { UsageDataPoint } from '@/types/api';

interface UsageChartProps {
  data: UsageDataPoint[];
}

export function UsageChart({ data }: UsageChartProps) {
  const max = useMemo(
    () => Math.max(...data.map((d) => d.query_count), 1),
    [data],
  );

  if (data.length === 0) {
    return (
      <div className="flex h-36 items-center justify-center text-sm text-slate-500">
        No usage data yet
      </div>
    );
  }

  return (
    <div className="flex h-36 items-end gap-1">
      {data.map((point) => {
        const heightPct = (point.query_count / max) * 100;
        const date = new Date(point.date);
        const label = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        return (
          <div
            key={point.date}
            className="group relative flex flex-1 flex-col items-center justify-end"
            style={{ height: '100%' }}
          >
            <div
              className="w-full rounded-t-sm bg-blue-600/70 transition-all group-hover:bg-blue-500"
              style={{ height: `${Math.max(heightPct, 2)}%` }}
            />
            {/* Tooltip */}
            <div className="absolute bottom-full mb-1 hidden rounded bg-slate-700 px-2 py-1 text-xs text-white group-hover:block whitespace-nowrap">
              {label}: {point.query_count} queries
            </div>
          </div>
        );
      })}
    </div>
  );
}
