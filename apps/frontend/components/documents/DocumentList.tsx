'use client';

import { Trash2, RefreshCw } from 'lucide-react';
import { useDocuments, useDeleteDocument } from '@/hooks/useDocuments';
import { DocumentStatusBadge } from './DocumentStatusBadge';
import { Skeleton } from '@/components/ui/Skeleton';
import { Button } from '@/components/ui/Button';
import { formatDate, formatBytes } from '@/lib/utils';

interface DocumentListProps {
  collectionId?: string;
}

export function DocumentList({ collectionId }: DocumentListProps) {
  const { data: docs, isLoading, refetch } = useDocuments(collectionId);
  const deleteMutation = useDeleteDocument();

  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    );
  }

  if (!docs || docs.length === 0) {
    return (
      <div className="py-12 text-center text-sm text-slate-500">
        No documents yet. Upload one above.
      </div>
    );
  }

  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <p className="text-xs text-slate-500">{docs.length} document{docs.length !== 1 ? 's' : ''}</p>
        <Button variant="ghost" size="icon" onClick={() => refetch()} aria-label="Refresh">
          <RefreshCw className="h-3.5 w-3.5" />
        </Button>
      </div>
      <div className="overflow-hidden rounded-xl border border-slate-800">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-800 bg-slate-900">
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-400">Name</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-400">Status</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-400">Chunks</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-400">Size</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-400">Uploaded</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {docs.map((doc) => (
              <tr
                key={doc.id}
                className="border-b border-slate-800 bg-slate-900/50 hover:bg-slate-800/50"
              >
                <td className="max-w-[200px] truncate px-4 py-3 font-medium text-white">
                  {doc.filename}
                </td>
                <td className="px-4 py-3">
                  <DocumentStatusBadge status={doc.status} />
                </td>
                <td className="px-4 py-3 text-slate-400">
                  {doc.num_chunks > 0 ? doc.num_chunks : '—'}
                </td>
                <td className="px-4 py-3 text-slate-400">
                  {formatBytes(doc.file_size)}
                </td>
                <td className="px-4 py-3 text-slate-400">
                  {formatDate(doc.created_at)}
                </td>
                <td className="px-4 py-3">
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => deleteMutation.mutate(doc.id)}
                    disabled={deleteMutation.isPending}
                    className="text-slate-500 hover:text-red-400"
                    aria-label="Delete document"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
