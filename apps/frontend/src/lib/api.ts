import { Document, UploadRequest, UploadResponse } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// For Phase 1 we use an org ID stub.
const ORG_ID_STUB = "11111111-1111-1111-1111-111111111111";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-Org-ID": ORG_ID_STUB,
      ...init?.headers,
    },
  });

  if (!res.ok) {
    let errorText = await res.text();
    throw new Error(`API ${res.status}: ${errorText}`);
  }
  
  // Some endpoints return 202 without body.
  const contentType = res.headers.get("content-type");
  if (contentType && contentType.includes("application/json")) {
    return res.json() as Promise<T>;
  }
  return {} as T;
}

export const api = {
  documents: {
    list: () => apiFetch<Document[]>("/v1/documents"),
    upload: (body: UploadRequest) =>
      apiFetch<UploadResponse>("/v1/documents", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    process: (id: string, pathUrl: string) =>
      apiFetch<{ status: string; job_id: string }>(`/v1/documents/${id}/process`, {
        method: "POST",
        body: JSON.stringify({ s3_path: pathUrl }),
      }),
  },
};
