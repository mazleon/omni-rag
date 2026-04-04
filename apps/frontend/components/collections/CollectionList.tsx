'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { FolderOpen, Pencil, Trash2, Plus, FileText } from 'lucide-react';
import { useCollections, useDeleteCollection } from '@/hooks/useCollections';
import { CollectionForm } from './CollectionForm';
import { Button } from '@/components/ui/Button';
import { Skeleton } from '@/components/ui/Skeleton';
import { Card } from '@/components/ui/Card';
import { formatDate } from '@/lib/utils';
import type { Collection } from '@/types/api';

export function CollectionList() {
  const router = useRouter();
  const { data: collections, isLoading } = useCollections();
  const deleteMutation = useDeleteCollection();
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Collection | undefined>();

  if (isLoading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-32" />
        ))}
      </div>
    );
  }

  const handleCollectionClick = (col: Collection) => {
    router.push(`/documents?collection=${col.id}`);
  };

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <p className="text-sm text-slate-400">
          {collections?.length ?? 0} collection{collections?.length !== 1 ? 's' : ''}
        </p>
        <Button size="sm" onClick={() => { setEditing(undefined); setFormOpen(true); }}>
          <Plus className="h-4 w-4" />
          New collection
        </Button>
      </div>

      {!collections || collections.length === 0 ? (
        <div className="rounded-xl border-2 border-dashed border-slate-800 py-16 text-center">
          <FolderOpen className="mx-auto mb-3 h-8 w-8 text-slate-600" />
          <p className="text-sm text-slate-500">No collections yet</p>
          <Button
            variant="ghost"
            size="sm"
            className="mt-3"
            onClick={() => setFormOpen(true)}
          >
            Create your first collection
          </Button>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {collections.map((col) => (
            <Card
              key={col.id}
              className="flex flex-col justify-between gap-4 cursor-pointer hover:border-blue-500/50 transition-colors group"
              onClick={() => handleCollectionClick(col)}
            >
              <div>
                <div className="mb-1 flex items-center gap-2">
                  <FolderOpen className="h-4 w-4 text-blue-400 group-hover:text-blue-300 transition-colors" />
                  <h3 className="font-medium text-white">{col.name}</h3>
                </div>
                {col.description && (
                  <p className="text-xs text-slate-500 line-clamp-2">{col.description}</p>
                )}
              </div>
              <div className="flex items-center justify-between text-xs text-slate-500">
                <span className="flex items-center gap-1">
                  <FileText className="h-3 w-3" />
                  {col.document_count} doc{col.document_count !== 1 ? 's' : ''}
                  {' · '}
                  {formatDate(col.created_at)}
                </span>
                <div className="flex gap-1" onClick={(e) => e.stopPropagation()}>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => { setEditing(col); setFormOpen(true); }}
                    aria-label="Edit"
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => deleteMutation.mutate(col.id)}
                    disabled={deleteMutation.isPending}
                    className="text-slate-500 hover:text-red-400"
                    aria-label="Delete"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      <CollectionForm
        open={formOpen}
        onClose={() => setFormOpen(false)}
        existing={editing}
      />
    </div>
  );
}
