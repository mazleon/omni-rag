"use client";

import { Message } from "ai";
import { Citation } from "@/lib/types";
import { CitationCard } from "./CitationCard";
import { User, Cpu } from "lucide-react";

export function MessageList({ messages }: { messages: Message[] }) {
  if (messages.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-center animate-in fade-in duration-700">
        <div className="size-16 rounded-3xl bg-brand/10 text-brand flex items-center justify-center mb-6 shadow-inner border border-brand/20">
          <Cpu className="size-8" />
        </div>
        <h2 className="text-2xl font-bold tracking-tight text-foreground mb-3">
          OmniRAG Intelligence
        </h2>
        <p className="max-w-md text-muted-foreground text-sm leading-relaxed">
          Ask questions across your entire organization's knowledge base. OmniRAG uses 
          hybrid reasoning to extract, synthesize, and cite every answer.
        </p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 py-8 space-y-8 scroll-smooth">
      {messages.map((m) => (
        <div
          key={m.id}
          className={`group flex items-start gap-4 mx-auto max-w-4xl w-full ${
            m.role === "user" ? "flex-row-reverse" : "flex-row"
          } animate-in slide-in-from-bottom-2 fade-in duration-300`}
        >
          {/* Avatar Icon */}
          <div
            className={`shrink-0 flex items-center justify-center size-9 rounded-full ring-1 shadow-sm ${
              m.role === "user"
                ? "bg-foreground text-background ring-border"
                : "bg-brand text-brand-foreground ring-brand/50 shadow-brand/10"
            }`}
          >
            {m.role === "user" ? <User className="size-4" /> : <Cpu className="size-4" />}
          </div>

          {/* Message Content bubble */}
          <div
            className={`flex flex-col gap-3 min-w-0 max-w-[85%] ${
              m.role === "user" ? "items-end" : "items-start"
            }`}
          >
            <div
              className={`px-5 py-3.5 rounded-2xl ${
                m.role === "user"
                  ? "bg-muted/60 text-foreground rounded-tr-sm"
                  : "bg-background border border-border/60 shadow-sm glass rounded-tl-sm text-foreground/90 leading-relaxed tracking-wide"
              }`}
            >
              <div className="prose prose-sm dark:prose-invert prose-p:leading-relaxed prose-pre:bg-muted/50 prose-pre:border max-w-none">
                {m.content}
              </div>
            </div>

            {/* Citations if available */}
            {m.role === "assistant" && m.annotations && m.annotations.length > 0 && (
              <div className="mt-2 w-full glass p-3 rounded-xl border border-brand/10">
                <p className="text-xs font-semibold text-muted-foreground mb-3 uppercase tracking-wider px-1">
                  Reference Grounding
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {(m.annotations as Citation[]).map((cit, idx) => (
                    <CitationCard key={cit.chunk_id || idx} citation={cit} index={idx} />
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
