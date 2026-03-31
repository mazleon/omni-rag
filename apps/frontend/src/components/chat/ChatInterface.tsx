"use client";

import { useChat } from "@ai-sdk/react";
import { SendHorizonal, Loader2 } from "lucide-react";
import { MessageList } from "./MessageList";
import { Button } from "../ui/button";
import { Input } from "../ui/input";

export function ChatInterface() {
  // @ts-ignore - Vercel AI SDK version mismatch typings bypass
  const { messages, input, handleInputChange, handleSubmit, isLoading } = useChat({
    api: "/api/chat",
    // We expect the FASTAPI to yield Vercel AI SDK compatible text stream 
    // or standard JSON objects handled via custom parsing. We'll use "text" proxy.
  } as any);

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] relative w-full max-w-5xl mx-auto rounded-3xl mt-4 border bg-background/50 glass shadow-2xl overflow-hidden animate-in fade-in duration-500">
      
      {/* Scrollable messages area */}
      <div className="flex-1 overflow-y-auto w-full relative">
        <MessageList messages={messages} />
      </div>

      {/* Input area */}
      <div className="p-4 mx-4 mb-4 mt-2">
        <form 
          onSubmit={handleSubmit} 
          className="relative flex items-end gap-2 p-2 bg-background border rounded-2xl shadow-sm focus-within:ring-2 focus-within:ring-brand/50 transition-all ease-in-out duration-300"
        >
          <Input
            value={input}
            onChange={handleInputChange}
            placeholder="Query your enterprise knowledge base..."
            disabled={isLoading}
            className="flex-1 border-0 ring-0 focus-visible:ring-0 px-4 py-6 text-base bg-transparent placeholder:text-muted-foreground/50 shadow-none resize-none"
          />
          <Button 
            disabled={!(input || '').trim() || isLoading} 
            type="submit" 
            size="icon"
            className="rounded-xl h-12 w-12 shrink-0 bg-brand text-brand-foreground hover:bg-brand/90 transition-colors shadow-md shadow-brand/20 active:scale-95 disabled:opacity-50"
          >
            {isLoading ? <Loader2 className="size-5 animate-spin" /> : <SendHorizonal className="size-5" />}
          </Button>
        </form>
        <p className="text-center text-[10px] text-muted-foreground/60 mt-4 font-mono">
          OmniRAG V1 — Answers are algorithmically ranked and cited. Model hallucinations possible.
        </p>
      </div>

    </div>
  );
}
