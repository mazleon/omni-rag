"use client";

import { useState, useEffect } from "react";
import { DocumentCard } from "./DocumentCard";
import { DocumentUploader } from "./DocumentUploader";
import { api } from "@/lib/api";
import { Document, UploadRequest } from "@/lib/types";

export function DocumentLibrary() {
  const [docs, setDocs] = useState<Document[]>([]);

  // Simple Phase 1 mockup fetcher
  useEffect(() => {
    async function init() {
      try {
        const _docs = await api.documents.list();
        setDocs(_docs);
      } catch (err) {
        console.error("Listing failed", err);
      }
    }
    init();
  }, []);

  const handleUpload = async (file: File) => {
    // 1. Get presigned URL
    const req: UploadRequest = {
      filename: file.name,
      file_size_bytes: file.size,
      mime_type: file.type || "application/octet-stream",
    };
    
    try {
      // 2. We skip supabase SDK direct put for the skeleton 
      //    and trigger the backend pipeline directly for the demo
      const { document_id, presigned_url } = await api.documents.upload(req);
      
      // MOCK S3 UPLOAD for Skeleton
      await new Promise((r) => setTimeout(r, 600));

      // 3. Trigger ingest pipeline via Arq
      await api.documents.process(document_id, presigned_url);

      // 4. Update local state
      setDocs((prev) => [
        {
          id: document_id,
          organization_id: "stuborg",
          filename: file.name,
          file_size_bytes: file.size,
          mime_type: file.type,
          status: "processing",
          error_message: null,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
        ...prev,
      ]);
    } catch (error) {
      console.error("Failed to upload", error);
    }
  };

  return (
    <div className="flex flex-col gap-10">
      <section className="animate-in fade-in slide-in-from-bottom-2 duration-500 delay-100">
        <h2 className="text-xl font-bold tracking-tight text-foreground mb-4">Ingest New Data</h2>
        <DocumentUploader onUpload={handleUpload} />
      </section>

      <section className="animate-in fade-in slide-in-from-bottom-4 duration-500 delay-200">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold tracking-tight text-foreground">Knowledge Base</h2>
          <span className="text-sm font-mono text-muted-foreground bg-muted/30 px-2 py-1 rounded-md">{docs.length} assets</span>
        </div>
        {docs.length === 0 ? (
          <div className="text-center p-12 border border-dashed rounded-xl bg-card/20 text-muted-foreground">
            No documents uploaded yet.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {docs.map((d) => (
              <DocumentCard key={d.id} doc={d} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
