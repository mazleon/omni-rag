'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { documentsApi } from '@/lib/api';
import type { Document } from '@/types/api';

export function useDocuments(collectionId?: string) {
  return useQuery({
    queryKey: ['documents', collectionId],
    queryFn: () => documentsApi.list({ collection_id: collectionId, limit: 100 }),
  });
}

export function useDocumentStatus(documentId: string | null, enabled: boolean) {
  return useQuery({
    queryKey: ['document-status', documentId],
    queryFn: () => documentsApi.status(documentId!),
    enabled: enabled && documentId !== null,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === 'completed' || status === 'failed') return false;
      return 3000;
    },
  });
}

export function useUploadDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ file, collectionId }: { file: File; collectionId?: string }) =>
      documentsApi.upload(file, collectionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });
}

export function useDeleteDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => documentsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });
}
