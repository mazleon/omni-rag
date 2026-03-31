import { DocumentLibrary } from "@/components/documents/DocumentLibrary";

export const metadata = {
  title: "OmniRAG — Document Assets",
  description: "Ingest and manage PDF, Word, and Excel assets.",
};

export default function DocumentsPage() {
  return (
    <div className="flex flex-col h-full w-full max-w-7xl mx-auto xl:px-8 pb-10">
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight text-foreground">Assets</h1>
        <p className="text-muted-foreground mt-1 text-lg">Manage connected knowledge sources and view processing statuses.</p>
      </div>
      <DocumentLibrary />
    </div>
  );
}
