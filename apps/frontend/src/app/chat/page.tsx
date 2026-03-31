import { ChatInterface } from "@/components/chat/ChatInterface";

export const metadata = {
  title: "OmniRAG — Intelligence Chat",
  description: "Query your organization's documents with cited answers.",
};

export default function ChatPage() {
  return (
    <div className="flex flex-col h-full w-full mx-auto animate-in fade-in duration-500">
      <div className="mb-2">
        <h1 className="text-2xl font-bold tracking-tight text-foreground">Query Intelligence</h1>
        <p className="text-sm text-muted-foreground">Ask questions over indexed internal knowledge.</p>
      </div>
      <ChatInterface />
    </div>
  );
}
