---
name: omnirag-frontend
description: Frontend development and design patterns for OmniRAG — Next.js 15 RSC, shadcn/ui, Tailwind v4, Vercel AI SDK, SSE streaming, citation cards
version: 1.0.0
source: project-spec
triggers:
  - "frontend"
  - "UI"
  - "component"
  - "page"
  - "design"
  - "chat"
  - "streaming"
  - "next.js"
  - "shadcn"
---

# OmniRAG Frontend Development

You are building the frontend for **OmniRAG** using **Next.js 15** (App Router, React Server Components), **shadcn/ui**, **Tailwind v4**, and the **Vercel AI SDK** for streaming. Follow these patterns precisely.

---

## Project Layout

```
apps/frontend/
├── app/
│   ├── layout.tsx          # Root layout (fonts, theme provider)
│   ├── page.tsx            # Home / redirect to /chat
│   ├── chat/
│   │   ├── page.tsx        # Main chat interface (RSC)
│   │   └── [id]/page.tsx   # Specific conversation
│   ├── documents/
│   │   ├── page.tsx        # Document library
│   │   └── upload/page.tsx # Upload flow
│   └── api/
│       └── chat/route.ts   # Route handler (proxies to FastAPI SSE)
├── components/
│   ├── ui/                 # shadcn/ui generated components (do not hand-edit)
│   ├── chat/
│   │   ├── ChatInterface.tsx    # Main chat shell
│   │   ├── MessageList.tsx      # Scrollable message history
│   │   ├── MessageBubble.tsx    # User / assistant message
│   │   ├── StreamingMessage.tsx # Streams tokens via useChat
│   │   ├── CitationCard.tsx     # Inline citation reference
│   │   └── CitationPanel.tsx    # Side panel with source excerpts
│   ├── documents/
│   │   ├── DocumentUploader.tsx # Drag-drop upload with progress
│   │   ├── DocumentCard.tsx     # Status: pending|processing|indexed|error
│   │   └── DocumentLibrary.tsx  # Paginated grid
│   └── layout/
│       ├── Sidebar.tsx
│       └── TopBar.tsx
└── lib/
    ├── api.ts              # Typed fetch client for FastAPI
    ├── streaming.ts        # SSE consumer utilities
    └── types.ts            # Shared TypeScript types mirroring backend schemas
```

---

## Next.js 15 Conventions

### Always use the App Router — no Pages Router
### Server Components by default; add `"use client"` only when needed (interactivity, hooks, browser APIs)

```tsx
// app/chat/page.tsx — Server Component (default, no directive needed)
import { ChatInterface } from "@/components/chat/ChatInterface"

export default async function ChatPage() {
  // fetch initial data server-side
  const initialDocs = await fetchDocuments()
  return <ChatInterface initialDocs={initialDocs} />
}
```

```tsx
// components/chat/ChatInterface.tsx — Client Component (needs state/effects)
"use client"

import { useChat } from "ai/react"
```

### Metadata pattern
```tsx
import type { Metadata } from "next"

export const metadata: Metadata = {
  title: "OmniRAG — Chat",
  description: "Query your documents with AI",
}
```

---

## Vercel AI SDK (SSE streaming)

### Install: `npm install ai`

### useChat hook for streaming from the FastAPI SSE endpoint:
```tsx
"use client"
import { useChat } from "ai/react"

export function ChatInterface() {
  const { messages, input, handleInputChange, handleSubmit, isLoading } = useChat({
    api: "/api/chat",          // Next.js route handler that proxies to FastAPI
    streamProtocol: "text",    // FastAPI sends raw SSE
    onFinish: (message) => {
      // parse citations from message.annotations
    },
  })

  return (
    <div className="flex flex-col h-screen">
      <MessageList messages={messages} />
      <ChatInput
        value={input}
        onChange={handleInputChange}
        onSubmit={handleSubmit}
        disabled={isLoading}
      />
    </div>
  )
}
```

### Route handler (`app/api/chat/route.ts`) — proxies to FastAPI SSE:
```ts
import { NextRequest } from "next/server"

export async function POST(req: NextRequest) {
  const body = await req.json()
  const apiRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/v1/query`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: req.headers.get("Authorization") ?? "",
    },
    body: JSON.stringify(body),
  })
  // Stream the FastAPI SSE response directly to the client
  return new Response(apiRes.body, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  })
}
```

---

## shadcn/ui Usage

### Install components with CLI, never hand-write them:
```bash
npx shadcn@latest add button card input textarea badge scroll-area separator sheet tooltip
```

### Installed components live in `components/ui/` — treat as read-only
### Always import from `@/components/ui/<component>`:
```tsx
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
```

---

## Tailwind v4 Patterns

### Config is in `app/globals.css` (not `tailwind.config.js` for v4):
```css
@import "tailwindcss";

@theme {
  --color-brand: oklch(55% 0.2 250);
  --color-brand-foreground: oklch(98% 0 0);
  --font-sans: "Inter Variable", sans-serif;
  --font-mono: "JetBrains Mono Variable", monospace;
}
```

### Design tokens for OmniRAG UI:
```tsx
// Primary action buttons
<Button className="bg-brand text-brand-foreground hover:bg-brand/90">

// Processing/indexing status badges
const statusColor = {
  pending:    "bg-yellow-100 text-yellow-800",
  processing: "bg-blue-100 text-blue-800",
  indexed:    "bg-green-100 text-green-800",
  error:      "bg-red-100 text-red-800",
}

// Chat layout: full-height flex column
<div className="flex flex-col h-dvh overflow-hidden">
```

---

## Citation Card Component

```tsx
// components/chat/CitationCard.tsx
interface Citation {
  chunk_id: string
  document_id: string
  document_title: string
  page_number: number
  relevance_score: number
  excerpt: string
}

export function CitationCard({ citation, index }: { citation: Citation; index: number }) {
  return (
    <Card className="cursor-pointer hover:ring-2 hover:ring-brand transition-all">
      <CardHeader className="py-2 px-3">
        <div className="flex items-center justify-between gap-2">
          <Badge variant="outline">[{index + 1}]</Badge>
          <span className="text-xs text-muted-foreground truncate flex-1">
            {citation.document_title}
          </span>
          <span className="text-xs text-muted-foreground">p.{citation.page_number}</span>
        </div>
      </CardHeader>
      <CardContent className="py-2 px-3">
        <p className="text-xs text-muted-foreground line-clamp-3">{citation.excerpt}</p>
      </CardContent>
    </Card>
  )
}
```

---

## Document Upload Component

```tsx
"use client"
import { useCallback, useState } from "react"
import { useDropzone } from "react-dropzone"  // npm install react-dropzone

const ACCEPTED_TYPES = {
  "application/pdf": [".pdf"],
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
  "application/vnd.openxmlformats-officedocument.presentationml.presentation": [".pptx"],
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
  "image/png": [".png"],
  "image/jpeg": [".jpg", ".jpeg"],
  "text/html": [".html"],
  "text/markdown": [".md"],
}

export function DocumentUploader({ onUpload }: { onUpload: (file: File) => Promise<void> }) {
  const [uploading, setUploading] = useState(false)

  const onDrop = useCallback(async (files: File[]) => {
    setUploading(true)
    for (const file of files) await onUpload(file)
    setUploading(false)
  }, [onUpload])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED_TYPES,
    maxSize: 100 * 1024 * 1024,  // 100MB
  })

  return (
    <div
      {...getRootProps()}
      className={`border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-colors
        ${isDragActive ? "border-brand bg-brand/5" : "border-muted-foreground/25 hover:border-brand/50"}`}
    >
      <input {...getInputProps()} />
      {uploading ? (
        <p className="text-sm text-muted-foreground">Uploading...</p>
      ) : (
        <p className="text-sm text-muted-foreground">
          Drop PDF, DOCX, PPTX, XLSX, images, or Markdown — or click to browse
        </p>
      )}
    </div>
  )
}
```

---

## Typed API Client (`lib/api.ts`)

```ts
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  })
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`)
  return res.json() as Promise<T>
}

export const api = {
  documents: {
    list: () => apiFetch<Document[]>("/v1/documents"),
    upload: (body: UploadRequest) =>
      apiFetch<UploadResponse>("/v1/documents/upload", { method: "POST", body: JSON.stringify(body) }),
    process: (id: string) =>
      apiFetch<void>(`/v1/documents/${id}/process`, { method: "POST" }),
    delete: (id: string) =>
      apiFetch<void>(`/v1/documents/${id}`, { method: "DELETE" }),
  },
  feedback: {
    submit: (body: FeedbackRequest) =>
      apiFetch<void>("/v1/feedback", { method: "POST", body: JSON.stringify(body) }),
  },
}
```

---

## Environment Variables (frontend)

```bash
# apps/frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Rules to Never Break

- **No Pages Router** — App Router only
- **RSC by default** — add `"use client"` only when required (state, effects, event handlers)
- **No hand-editing `components/ui/`** — use `npx shadcn@latest add`
- **All streaming via Vercel AI SDK `useChat`** — no manual EventSource/fetch for SSE
- **Citation numbers must match** the `citations[]` array index in the `done` SSE event
- **Document status colours** must follow the 4-state palette (pending/processing/indexed/error)
- **Never expose `SUPABASE_SERVICE_ROLE_KEY` or `OPENROUTER_API_KEY` to the browser** — all sensitive calls go through the Next.js route handler
- **`NEXT_PUBLIC_*` variables only** for values safe to expose to the browser
