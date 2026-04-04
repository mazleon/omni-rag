'use client';

import { useQuery } from '@tanstack/react-query';
import { analyticsApi } from '@/lib/api';

export function useAnalyticsSummary(days = 30) {
  return useQuery({
    queryKey: ['analytics-summary', days],
    queryFn: () => analyticsApi.summary(days),
    staleTime: 60_000,
  });
}

export function useQueryHistory(limit = 20, offset = 0) {
  return useQuery({
    queryKey: ['query-history', limit, offset],
    queryFn: () => analyticsApi.queryHistory({ limit, offset }),
  });
}

export function useUsageData(days = 30) {
  return useQuery({
    queryKey: ['usage-data', days],
    queryFn: () => analyticsApi.usage(days),
    staleTime: 60_000,
  });
}
