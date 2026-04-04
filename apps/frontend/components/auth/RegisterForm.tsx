'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useAuth } from '@/hooks/useAuth';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';

export function RegisterForm() {
  const { register } = useAuth();
  const [form, setForm] = useState({
    email: '',
    password: '',
    full_name: '',
    org_name: '',
  });
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((prev) => ({ ...prev, [key]: e.target.value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);
    try {
      await register(form);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Registration failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <Input
        id="full_name"
        label="Full name"
        placeholder="Ada Lovelace"
        value={form.full_name}
        onChange={set('full_name')}
        autoComplete="name"
      />
      <Input
        id="org_name"
        label="Organization name"
        placeholder="Acme Corp"
        value={form.org_name}
        onChange={set('org_name')}
      />
      <Input
        id="email"
        type="email"
        label="Email"
        placeholder="you@company.com"
        value={form.email}
        onChange={set('email')}
        required
        autoComplete="email"
      />
      <Input
        id="password"
        type="password"
        label="Password"
        placeholder="min 8 characters"
        value={form.password}
        onChange={set('password')}
        required
        minLength={8}
        autoComplete="new-password"
      />
      {error && <p className="text-sm text-red-400">{error}</p>}
      <Button type="submit" className="w-full" isLoading={isLoading}>
        Create account
      </Button>
      <p className="text-center text-sm text-slate-400">
        Already have an account?{' '}
        <Link href="/login" className="text-blue-400 hover:underline">
          Sign in
        </Link>
      </p>
    </form>
  );
}
