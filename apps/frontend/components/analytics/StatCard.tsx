import { cn } from '@/lib/utils';
import type { LucideIcon } from 'lucide-react';

interface StatCardProps {
  label: string;
  value: string | number;
  icon: LucideIcon;
  sub?: string;
  highlight?: boolean;
}

export function StatCard({ label, value, icon: Icon, sub, highlight }: StatCardProps) {
  return (
    <div
      className={cn(
        'rounded-xl border p-5',
        highlight
          ? 'border-blue-700/40 bg-blue-600/10'
          : 'border-slate-800 bg-slate-900',
      )}
    >
      <div className="mb-3 flex items-center justify-between">
        <span className="text-xs font-medium text-slate-400">{label}</span>
        <div
          className={cn(
            'flex h-8 w-8 items-center justify-center rounded-lg',
            highlight ? 'bg-blue-600/20' : 'bg-slate-800',
          )}
        >
          <Icon className={cn('h-4 w-4', highlight ? 'text-blue-400' : 'text-slate-400')} />
        </div>
      </div>
      <p className="text-2xl font-bold text-white">{value}</p>
      {sub && <p className="mt-0.5 text-xs text-slate-500">{sub}</p>}
    </div>
  );
}
