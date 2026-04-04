import { ApiKeyList } from '@/components/settings/ApiKeyList';

export const metadata = { title: 'API Keys — OmniRAG' };

export default function ApiKeysPage() {
  return (
    <div className="p-6 max-w-4xl space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-white mb-1">API Keys</h2>
        <p className="text-sm text-slate-400">
          Generate API keys to call OmniRAG programmatically. Keys start with{' '}
          <code className="rounded bg-slate-800 px-1 font-mono text-xs">onr_</code>.
        </p>
      </div>
      <ApiKeyList />
    </div>
  );
}
