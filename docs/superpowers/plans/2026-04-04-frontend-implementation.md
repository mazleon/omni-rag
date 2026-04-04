# OmniRAG Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a production-quality Next.js 14 frontend for OmniRAG with auth, SSE-streaming chat, document/collection management, analytics, and API key management.

**Architecture:** Route-group layout — `(auth)` for public login/register pages, `(app)` for JWT-protected shell with sidebar nav. TanStack Query for server state, React Context for auth, native fetch SSE for streaming chat.

**Tech Stack:** Next.js 14 + Tailwind v3 + CVA + lucide-react + @tanstack/react-query (all already in package.json — no new deps needed for core features).

---

## File Map

| File | Responsibility |
|---|---|
| `types/api.ts` | All API request/response types |
| `lib/utils.ts` | `cn()` helper |
| `lib/auth.ts` | localStorage token read/write/clear |
| `lib/api.ts` | Auth-aware API client (replaces existing) |
| `context/AuthContext.tsx` | JWT auth state + login/logout actions |
| `hooks/useAuth.ts` | Auth context consumer |
| `hooks/useDocuments.ts` | TanStack Query document CRUD + status polling |
| `hooks/useCollections.ts` | TanStack Query collections CRUD |
| `hooks/useChat.ts` | SSE streaming chat state machine |
| `hooks/useAnalytics.ts` | TanStack Query analytics data |
| `components/ui/` | Button, Input, Badge, Card, Dialog, Skeleton (CVA-based) |
| `components/layout/AppShell.tsx` | Sidebar + topbar wrapper |
| `components/layout/Sidebar.tsx` | Nav links + branding |
| `components/layout/Topbar.tsx` | Page title + user menu |
| `components/auth/LoginForm.tsx` | Login form with validation |
| `components/auth/RegisterForm.tsx` | Register form with org name |
| `components/chat/ChatInterface.tsx` | Orchestrates chat state |
| `components/chat/MessageBubble.tsx` | Message with citations + feedback |
| `components/chat/SourceCard.tsx` | Expandable citation chip |
| `components/chat/ChatInput.tsx` | Textarea + send button |
| `components/documents/DocumentList.tsx` | Table with status polling |
| `components/documents/UploadDropzone.tsx` | Drag-and-drop uploader |
| `components/documents/DocumentStatusBadge.tsx` | Status pill |
| `components/collections/CollectionList.tsx` | Collection cards |
| `components/collections/CollectionForm.tsx` | Create/edit modal |
| `components/analytics/StatCard.tsx` | Single KPI metric card |
| `components/analytics/QueryHistoryTable.tsx` | Paginated query log |
| `components/analytics/UsageChart.tsx` | SVG bar chart (no deps) |
| `components/settings/ApiKeyList.tsx` | Create/revoke API keys |
| `app/layout.tsx` | Root layout with QueryClient + AuthProvider |
| `app/page.tsx` | Redirect → /chat or /login |
| `app/(auth)/login/page.tsx` | Login page |
| `app/(auth)/register/page.tsx` | Register page |
| `app/(app)/layout.tsx` | Auth guard + AppShell |
| `app/(app)/chat/page.tsx` | Main chat page |
| `app/(app)/documents/page.tsx` | Document manager page |
| `app/(app)/collections/page.tsx` | Collections page |
| `app/(app)/analytics/page.tsx` | Analytics dashboard |
| `app/(app)/settings/api-keys/page.tsx` | API keys settings page |
