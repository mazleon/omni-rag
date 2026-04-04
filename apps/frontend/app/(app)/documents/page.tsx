'use client';

import { useState, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import { UploadDropzone } from '@/components/documents/UploadDropzone';
import { DocumentList } from '@/components/documents/DocumentList';
import { useUploadDocument } from '@/hooks/useDocuments';
import { useCollections } from '@/hooks/useCollections';

export default function DocumentsPage() {
  const searchParams = useSearchParams();
  const collectionParam = searchParams?.get('collection') ?? undefined;

  const uploadMutation = useUploadDocument();
  const { data: collections } = useCollections();
  const [selectedCollection, setSelectedCollection] = useState<string | undefined>(collectionParam);

  useEffect(() => {
    if (collectionParam) {
      setSelectedCollection(collectionParam);
    }
  }, [collectionParam]);

  const handleUpload = (file: File) => {
    uploadMutation.mutate({ file, collectionId: selectedCollection });
  };

  return (
    <div className="p-6 space-y-6 max-w-6xl">
      <div>
        <h2 className="text-lg font-semibold text-white mb-1">Documents</h2>
        <p className="text-sm text-slate-400">
          Upload documents to ingest into your knowledge base.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-1 space-y-4">
          {collections && collections.length > 0 && (
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-400">
                Collection (optional)
              </label>
              <select
                value={selectedCollection ?? ''}
                onChange={(e) => setSelectedCollection(e.target.value || undefined)}
                className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white focus:border-blue-500 focus:outline-none"
              >
                <option value="">All documents</option>
                {collections.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
          )}
          <UploadDropzone
            onUpload={handleUpload}
            isUploading={uploadMutation.isPending}
          />
          {uploadMutation.isError && (
            <p className="text-sm text-red-400">
              {uploadMutation.error instanceof Error
                ? uploadMutation.error.message
                : 'Upload failed'}
            </p>
          )}
        </div>

        <div className="lg:col-span-2">
          <DocumentList collectionId={selectedCollection} />
        </div>
      </div>
    </div>
  );
}
