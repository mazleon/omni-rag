import { getToken } from './auth';
import type {
  TokenResponse,
  UserCreate,
  UserLogin,
  UserProfile,
  Document,
  DocumentUploadResponse,
  DocumentStatusResponse,
  Collection,
  CollectionListResponse,
  QueryResponse,
  StreamChunk,
  AnalyticsSummary,
  QueryHistoryResponse,
  UsageDataPoint,
  FeedbackRequest,
  ApiKey,
  ApiKeyWithSecret,
  ApiKeyCreateRequest,
} from '@/types/api';

interface UsageApiResponse {
  usage: UsageDataPoint[];
  period_days: number;
}

const BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/v1';

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${BASE}${endpoint}`, { ...options, headers });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
    throw new ApiError(res.status, body.detail ?? `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

// ─── Auth ──────────────────────────────────────────────────────────────────
export const authApi = {
  register: (data: UserCreate) =>
    request<TokenResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  login: (data: UserLogin) =>
    request<TokenResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  me: () => request<UserProfile>('/auth/me'),
};

// ─── Documents ─────────────────────────────────────────────────────────────
export const documentsApi = {
  list: (params?: { collection_id?: string; limit?: number; offset?: number }) => {
    const q = new URLSearchParams();
    if (params?.collection_id) q.set('collection_id', params.collection_id);
    if (params?.limit !== undefined) q.set('limit', String(params.limit));
    if (params?.offset !== undefined) q.set('offset', String(params.offset));
    return request<Document[]>(`/documents?${q}`);
  },

  upload: async (file: File, collectionId?: string): Promise<DocumentUploadResponse> => {
    const token = getToken();
    const formData = new FormData();
    formData.append('file', file);
    if (collectionId) formData.append('collection_id', collectionId);

    const res = await fetch(`${BASE}/documents/upload`, {
      method: 'POST',
      body: formData,
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({ detail: 'Upload failed' }));
      throw new ApiError(res.status, body.detail ?? 'Upload failed');
    }
    return res.json();
  },

  status: (id: string) =>
    request<DocumentStatusResponse>(`/documents/${id}/status`),

  delete: (id: string) =>
    request<void>(`/documents/${id}`, { method: 'DELETE' }),
};

// ─── Collections ───────────────────────────────────────────────────────────
export const collectionsApi = {
  list: (params?: { limit?: number; offset?: number }) => {
    const q = new URLSearchParams();
    if (params?.limit !== undefined) q.set('limit', String(params.limit));
    if (params?.offset !== undefined) q.set('offset', String(params.offset));
    return request<CollectionListResponse>(`/collections?${q}`);
  },

  create: (data: { name: string; description?: string }) =>
    request<Collection>('/collections', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (id: string, data: { name?: string; description?: string }) =>
    request<Collection>(`/collections/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    request<void>(`/collections/${id}`, { method: 'DELETE' }),
};

// ─── Query ─────────────────────────────────────────────────────────────────
export const queryApi = {
  query: (text: string, collectionId?: string) =>
    request<QueryResponse>('/query', {
      method: 'POST',
      body: JSON.stringify({ query: text, collection_id: collectionId }),
    }),

  stream: async (
    text: string,
    onChunk: (chunk: StreamChunk) => void,
    collectionId?: string,
  ): Promise<void> => {
    const token = getToken();
    const res = await fetch(`${BASE}/query/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ query: text, collection_id: collectionId }),
    });

    if (!res.ok) {
      const body = await res.json().catch(() => ({ detail: 'Query failed' }));
      throw new ApiError(res.status, body.detail ?? 'Query failed');
    }

    const reader = res.body?.getReader();
    if (!reader) throw new Error('No response body');
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const text = decoder.decode(value, { stream: true });
      for (const line of text.split('\n')) {
        if (!line.startsWith('data: ')) continue;
        try {
          onChunk(JSON.parse(line.slice(6)) as StreamChunk);
        } catch {
          // skip malformed lines
        }
      }
    }
  },
};

// ─── Analytics ─────────────────────────────────────────────────────────────
export const analyticsApi = {
  summary: (days?: number) => {
    const q = days !== undefined ? `?days=${days}` : '';
    return request<AnalyticsSummary>(`/analytics/summary${q}`);
  },

  queryHistory: (params?: { limit?: number; offset?: number }) => {
    const q = new URLSearchParams();
    if (params?.limit !== undefined) q.set('limit', String(params.limit));
    if (params?.offset !== undefined) q.set('offset', String(params.offset));
    return request<QueryHistoryResponse>(`/analytics/queries/history?${q}`);
  },

  usage: (days?: number) => {
    const q = days !== undefined ? `?days=${days}` : '';
    return request<UsageApiResponse>(`/analytics/usage${q}`).then((r) => r.usage);
  },
};

// ─── Feedback ──────────────────────────────────────────────────────────────
export const feedbackApi = {
  submit: (data: FeedbackRequest) =>
    request('/feedback', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
};

// ─── API Keys ──────────────────────────────────────────────────────────────
export const apiKeysApi = {
  list: () => request<ApiKey[]>('/api-keys'),

  create: (data: ApiKeyCreateRequest) =>
    request<ApiKeyWithSecret>('/api-keys', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  revoke: (id: string) =>
    request<void>(`/api-keys/${id}`, { method: 'DELETE' }),
};

export { ApiError };
