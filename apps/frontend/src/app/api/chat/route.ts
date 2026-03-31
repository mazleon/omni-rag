import { NextRequest } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function POST(req: NextRequest) {
  const body = await req.json();
  const apiRes = await fetch(`${API_BASE}/v1/query/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: req.headers.get("Authorization") ?? "",
      "X-Org-ID": "11111111-1111-1111-1111-111111111111", // Phase 1 Stub
    },
    body: JSON.stringify({
      text: body.messages[body.messages.length - 1].content,
      stream: true,
    }),
  });

  if (!apiRes.ok) {
    const errorMsg = await apiRes.text();
    return new Response(`Backend Error ${apiRes.status}: ${errorMsg}`, {
      status: apiRes.status,
    });
  }

  // Stream the FastAPI SSE response directly to the AI SDK
  return new Response(apiRes.body, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}
