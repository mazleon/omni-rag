import { CollectionList } from '@/components/collections/CollectionList';

export const metadata = { title: 'Collections — OmniRAG' };

export default function CollectionsPage() {
  return (
    <div className="p-6 max-w-5xl space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-white mb-1">Collections</h2>
        <p className="text-sm text-slate-400">
          Group related documents into collections to scope your queries.
        </p>
      </div>
      <CollectionList />
    </div>
  );
}
