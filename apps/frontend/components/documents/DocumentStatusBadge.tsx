import { Badge } from '@/components/ui/Badge';
import type { DocumentStatus } from '@/types/api';

export function DocumentStatusBadge({ status }: { status: DocumentStatus }) {
  const map: Record<DocumentStatus, { label: string; variant: 'success' | 'warning' | 'error' | 'info' | 'default' }> = {
    completed: { label: 'Ready', variant: 'success' },
    processing: { label: 'Processing', variant: 'warning' },
    pending: { label: 'Pending', variant: 'info' },
    failed: { label: 'Failed', variant: 'error' },
  };
  const { label, variant } = map[status] ?? { label: status, variant: 'default' };
  return <Badge variant={variant}>{label}</Badge>;
}
