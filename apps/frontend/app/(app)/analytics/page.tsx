'use client';

import {
  MessageSquare,
  FileText,
  Zap,
  Clock,
  DollarSign,
  Activity,
} from 'lucide-react';
import { useAnalyticsSummary, useUsageData } from '@/hooks/useAnalytics';
import { StatCard } from '@/components/analytics/StatCard';
import { QueryHistoryTable } from '@/components/analytics/QueryHistoryTable';
import { UsageChart } from '@/components/analytics/UsageChart';
import { Card, CardHeader, CardTitle } from '@/components/ui/Card';
import { Skeleton } from '@/components/ui/Skeleton';
import { formatLatency } from '@/lib/utils';

export default function AnalyticsPage() {
  const { data: summary, isLoading: summaryLoading } = useAnalyticsSummary(30);
  const { data: usage } = useUsageData(30);

  return (
    <div className="p-6 max-w-6xl space-y-8">
      <div>
        <h2 className="text-lg font-semibold text-white mb-1">Analytics</h2>
        <p className="text-sm text-slate-400">Last 30 days</p>
      </div>

      {/* KPI grid */}
      {summaryLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
      ) : summary ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <StatCard
            label="Total queries"
            value={summary.total_queries.toLocaleString()}
            icon={MessageSquare}
            sub={`${summary.queries_today} today · ${summary.queries_this_week} this week`}
            highlight
          />
          <StatCard
            label="Documents ingested"
            value={summary.total_documents.toLocaleString()}
            icon={FileText}
          />
          <StatCard
            label="Avg latency"
            value={formatLatency(summary.avg_latency_ms)}
            icon={Clock}
            sub={`P95 ${formatLatency(summary.p95_latency_ms)} · P99 ${formatLatency(summary.p99_latency_ms)}`}
          />
          <StatCard
            label="Total tokens"
            value={summary.total_tokens.toLocaleString()}
            icon={Zap}
          />
          <StatCard
            label="Total cost"
            value={`$${summary.total_cost_usd.toFixed(4)}`}
            icon={DollarSign}
            sub={`~$${(summary.total_cost_usd / Math.max(summary.total_queries, 1)).toFixed(4)} avg/query`}
          />
          <StatCard
            label="P50 latency"
            value={formatLatency(summary.p50_latency_ms)}
            icon={Activity}
          />
        </div>
      ) : null}

      {/* Usage chart */}
      {usage && usage.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Daily queries — last 30 days</CardTitle>
          </CardHeader>
          <UsageChart data={usage} />
        </Card>
      )}

      {/* Query history */}
      <Card>
        <CardHeader>
          <CardTitle>Query history</CardTitle>
        </CardHeader>
        <QueryHistoryTable />
      </Card>
    </div>
  );
}
