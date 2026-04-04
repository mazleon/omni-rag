'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  MessageSquare,
  FileText,
  FolderOpen,
  BarChart2,
  Key,
  Zap,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const NAV = [
  { href: '/chat', label: 'Chat', icon: MessageSquare },
  { href: '/documents', label: 'Documents', icon: FileText },
  { href: '/collections', label: 'Collections', icon: FolderOpen },
  { href: '/analytics', label: 'Analytics', icon: BarChart2 },
  { href: '/settings/api-keys', label: 'API Keys', icon: Key },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-full w-60 flex-col border-r border-slate-800 bg-slate-950">
      {/* Brand */}
      <div className="flex items-center gap-2.5 px-5 py-5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600">
          <Zap className="h-4 w-4 text-white" />
        </div>
        <span className="text-base font-bold text-white tracking-tight">OmniRAG</span>
      </div>

      {/* Nav */}
      <nav className="flex-1 space-y-0.5 px-3 pb-4">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                active
                  ? 'bg-blue-600/15 text-blue-400'
                  : 'text-slate-400 hover:bg-slate-800 hover:text-white',
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Footer label */}
      <div className="px-5 pb-4">
        <p className="text-xs text-slate-600">Enterprise RAG Platform</p>
      </div>
    </aside>
  );
}
