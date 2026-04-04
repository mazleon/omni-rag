import { Zap } from 'lucide-react';
import { LoginForm } from '@/components/auth/LoginForm';

export const metadata = { title: 'Sign in — OmniRAG' };

export default function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 p-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-600">
            <Zap className="h-6 w-6 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white">Welcome back</h1>
          <p className="mt-1 text-sm text-slate-400">Sign in to your OmniRAG workspace</p>
        </div>
        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-8">
          <LoginForm />
        </div>
      </div>
    </div>
  );
}
