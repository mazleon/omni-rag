'use client';

import { useState } from 'react';
import { Copy, Trash2, Plus, Check, Eye, EyeOff } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiKeysApi } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { Dialog } from '@/components/ui/Dialog';
import { Skeleton } from '@/components/ui/Skeleton';
import { formatDate } from '@/lib/utils';
import type { ApiKeyWithSecret } from '@/types/api';

export function ApiKeyList() {
  const queryClient = useQueryClient();
  const { data: keys, isLoading } = useQuery({
    queryKey: ['api-keys'],
    queryFn: apiKeysApi.list,
  });

  const createMutation = useMutation({
    mutationFn: apiKeysApi.create,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['api-keys'] }),
  });

  const revokeMutation = useMutation({
    mutationFn: apiKeysApi.revoke,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['api-keys'] }),
  });

  const [formOpen, setFormOpen] = useState(false);
  const [newKey, setNewKey] = useState<ApiKeyWithSecret | null>(null);
  const [keyName, setKeyName] = useState('');
  const [copied, setCopied] = useState(false);
  const [visible, setVisible] = useState(false);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!keyName.trim()) return;
    const result = await createMutation.mutateAsync({ name: keyName.trim() });
    setNewKey(result);
    setKeyName('');
    setFormOpen(false);
  };

  const copyKey = async (key: string) => {
    await navigator.clipboard.writeText(key);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 2 }).map((_, i) => (
          <Skeleton key={i} className="h-14" />
        ))}
      </div>
    );
  }

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <p className="text-sm text-slate-400">
          {keys?.length ?? 0} key{keys?.length !== 1 ? 's' : ''}
        </p>
        <Button size="sm" onClick={() => setFormOpen(true)}>
          <Plus className="h-4 w-4" />
          New API key
        </Button>
      </div>

      {/* Newly-created key reveal banner */}
      {newKey && (
        <div className="mb-4 rounded-xl border border-emerald-700/40 bg-emerald-500/10 p-4">
          <p className="mb-2 text-sm font-medium text-emerald-400">
            Copy your key now — it won't be shown again.
          </p>
          <div className="flex items-center gap-2">
            <code className="flex-1 truncate rounded bg-slate-900 px-3 py-2 font-mono text-xs text-white">
              {visible ? newKey.api_key : '•'.repeat(40)}
            </code>
            <Button variant="ghost" size="icon" onClick={() => setVisible((v) => !v)}>
              {visible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </Button>
            <Button variant="ghost" size="icon" onClick={() => copyKey(newKey.api_key)}>
              {copied ? <Check className="h-4 w-4 text-emerald-400" /> : <Copy className="h-4 w-4" />}
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setNewKey(null)}>
              Dismiss
            </Button>
          </div>
        </div>
      )}

      {!keys || keys.length === 0 ? (
        <div className="rounded-xl border-2 border-dashed border-slate-800 py-12 text-center text-sm text-slate-500">
          No API keys yet.
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-800">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-900">
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-400">Name</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-400">Prefix</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-400">Rate limit</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-400">Status</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-400">Created</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {keys.map((key) => (
                <tr key={key.id} className="border-b border-slate-800 hover:bg-slate-800/30">
                  <td className="px-4 py-3 font-medium text-white">{key.name}</td>
                  <td className="px-4 py-3">
                    <code className="rounded bg-slate-800 px-1.5 py-0.5 font-mono text-xs text-slate-300">
                      {key.prefix}…
                    </code>
                  </td>
                  <td className="px-4 py-3 text-slate-400">
                    {key.rate_limit} req/{key.rate_window_seconds}s
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant={key.is_active ? 'success' : 'error'}>
                      {key.is_active ? 'Active' : 'Revoked'}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-slate-400">{formatDate(key.created_at)}</td>
                  <td className="px-4 py-3">
                    {key.is_active && (
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => revokeMutation.mutate(key.id)}
                        disabled={revokeMutation.isPending}
                        className="text-slate-500 hover:text-red-400"
                        aria-label="Revoke key"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Create dialog */}
      <Dialog open={formOpen} onClose={() => setFormOpen(false)} title="New API Key">
        <form onSubmit={handleCreate} className="space-y-4">
          <Input
            id="key-name"
            label="Key name"
            placeholder="e.g. production-app"
            value={keyName}
            onChange={(e) => setKeyName(e.target.value)}
            required
          />
          <div className="flex justify-end gap-2">
            <Button variant="secondary" type="button" onClick={() => setFormOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={createMutation.isPending}>
              Generate
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
}
