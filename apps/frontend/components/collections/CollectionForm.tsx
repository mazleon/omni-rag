'use client';

import { useState } from 'react';
import { Dialog } from '@/components/ui/Dialog';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { useCreateCollection, useUpdateCollection } from '@/hooks/useCollections';
import type { Collection } from '@/types/api';

interface CollectionFormProps {
  open: boolean;
  onClose: () => void;
  existing?: Collection;
}

export function CollectionForm({ open, onClose, existing }: CollectionFormProps) {
  const createMutation = useCreateCollection();
  const updateMutation = useUpdateCollection();
  const [name, setName] = useState(existing?.name ?? '');
  const [description, setDescription] = useState(existing?.description ?? '');
  const [error, setError] = useState('');

  const isLoading = createMutation.isPending || updateMutation.isPending;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!name.trim()) { setError('Name is required'); return; }
    try {
      if (existing) {
        await updateMutation.mutateAsync({ id: existing.id, data: { name, description } });
      } else {
        await createMutation.mutateAsync({ name, description });
      }
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to save collection');
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={existing ? 'Edit Collection' : 'New Collection'}
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          id="col-name"
          label="Name"
          placeholder="e.g. Legal contracts"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
        <div className="flex flex-col gap-1">
          <label htmlFor="col-desc" className="text-sm font-medium text-slate-300">
            Description <span className="text-slate-500">(optional)</span>
          </label>
          <textarea
            id="col-desc"
            rows={2}
            placeholder="What documents belong here?"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="w-full resize-none rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-400 focus:border-blue-500 focus:outline-none"
          />
        </div>
        {error && <p className="text-sm text-red-400">{error}</p>}
        <div className="flex justify-end gap-2">
          <Button variant="secondary" type="button" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" isLoading={isLoading}>
            {existing ? 'Save' : 'Create'}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
