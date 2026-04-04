'use client';

import { useState, useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { cn } from '@/lib/utils';
import {
  MessageSquare,
  FileText,
  FolderOpen,
  BarChart3,
  Key,
  LogOut,
  Menu,
  X,
} from 'lucide-react';

const NAV_ITEMS = [
  { href: '/chat', icon: MessageSquare, label: 'Chat' },
  { href: '/documents', icon: FileText, label: 'Documents' },
  { href: '/collections', icon: FolderOpen, label: 'Collections' },
  { href: '/analytics', icon: BarChart3, label: 'Analytics' },
  { href: '/settings/api-keys', icon: Key, label: 'API Keys' },
];

export function AppShell({ children, title }: { children: React.ReactNode; title: string }) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    setSidebarOpen(false);
  }, [pathname]);

  return (
    <div className="flex h-screen overflow-hidden bg-zinc-950 text-zinc-100">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/80 backdrop-blur-sm lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 w-64 transform border-r border-zinc-800 bg-zinc-900 transition-transform duration-200 ease-in-out lg:relative lg:translate-x-0',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <div className="flex h-full flex-col">
          {/* Logo */}
          <div className="flex items-center justify-between border-b border-zinc-800 px-4 h-14">
            <div className="flex items-center gap-2">
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-blue-600">
                <span className="text-xs font-bold text-white">O</span>
              </div>
              <span className="text-sm font-semibold">OmniRAG</span>
            </div>
            <button
              onClick={() => setSidebarOpen(false)}
              className="rounded-md p-1.5 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200 lg:hidden"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          {/* Nav */}
          <nav className="flex-1 space-y-0.5 p-3">
            {NAV_ITEMS.map((item) => {
              const isActive = pathname === item.href || pathname?.startsWith(item.href + '/');
              return (
                <button
                  key={item.href}
                  onClick={() => router.push(item.href)}
                  className={cn(
                    'flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-zinc-800 text-zinc-100'
                      : 'text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200',
                  )}
                >
                  <item.icon className="h-4 w-4" />
                  {item.label}
                </button>
              );
            })}
          </nav>

          {/* User */}
          <div className="border-t border-zinc-800 p-3">
            <div className="flex items-center gap-2.5 rounded-md px-2.5 py-2">
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-zinc-700 text-xs font-medium text-zinc-300">
                {user?.email?.[0]?.toUpperCase() ?? 'U'}
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-xs font-medium text-zinc-200">{user?.email}</p>
                <p className="truncate text-[10px] text-zinc-500 capitalize">{user?.role}</p>
              </div>
              <button
                onClick={logout}
                className="shrink-0 rounded-md p-1.5 text-zinc-500 hover:bg-zinc-800 hover:text-zinc-300"
                title="Sign out"
              >
                <LogOut className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        </div>
      </aside>

      {/* Main */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Topbar */}
        <header className="flex h-14 items-center border-b border-zinc-800 px-4 lg:px-6">
          <button
            onClick={() => setSidebarOpen(true)}
            className="mr-3 rounded-md p-1.5 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200 lg:hidden"
          >
            <Menu className="h-4 w-4" />
          </button>
          <h1 className="text-sm font-medium text-zinc-200">{title}</h1>
        </header>

        {/* Content */}
        <main className="flex-1 overflow-auto">{children}</main>
      </div>
    </div>
  );
}
