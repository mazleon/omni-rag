// ─── Auth ──────────────────────────────────────────────────────────────────
export interface UserCreate {
  email: string;
  password: string;
  full_name?: string;
  org_name?: string;
}

export interface UserLogin {
  email: string;
  password: string;
}

export interface UserProfile {
  id: string;
  email: string;
  full_name: string | null;
  role: string;
  org_id: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: UserProfile;
}

// ─── Documents ─────────────────────────────────────────────────────────────
export type DocumentStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface Document {
  id: string;
  filename: string;
  file_path: string;
  file_size: number | null;
  mime_type: string | null;
  content_hash: string;
  status: DocumentStatus;
  num_pages: number | null;
  num_chunks: number;
  error_message: string | null;
  collection_id: string | null;
  created_at: string;
  updated_at: string;
  processed_at: string | null;
}

export interface DocumentUploadResponse {
  document_id: string;
  upload_url: string;
  status: string;
}

export interface DocumentStatusResponse {
  document_id: string;
  status: DocumentStatus;
  num_chunks: number | null;
  error: string | null;
}

// ─── Collections ───────────────────────────────────────────────────────────
export interface Collection {
  id: string;
  name: string;
  description: string | null;
  document_count: number;
  created_at: string;
  updated_at: string;
}

export interface CollectionListResponse {
  collections: Collection[];
  total: number;
}

// ─── Query / Chat ───────────────────────────────────────────────────────────
export interface QuerySource {
  chunk_id: string;
  document_id: string;
  content: string;
  page_numbers: number[] | null;
  score: number;
  filename?: string;
}

export interface QueryResponse {
  query_id: string;
  answer: string;
  sources: QuerySource[];
  latency_ms: number;
  tokens_used: number | null;
  cost_usd: number | null;
  cached?: boolean;
  query_analysis?: Record<string, unknown>;
}

export interface StreamChunk {
  type: 'start' | 'content' | 'sources' | 'end' | 'error';
  content?: string;
  sources?: QuerySource[];
  query_id?: string;
  error?: string;
}

// ─── Analytics ─────────────────────────────────────────────────────────────
export interface AnalyticsSummary {
  total_queries: number;
  total_documents: number;
  avg_latency_ms: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
  total_tokens: number;
  total_cost_usd: number;
  queries_today: number;
  queries_this_week: number;
}

export interface QueryHistoryItem {
  id: string;
  query_text: string;
  answer: string | null;
  latency_ms: number | null;
  tokens_used: number | null;
  cost_usd: number | null;
  created_at: string;
}

export interface QueryHistoryResponse {
  queries: QueryHistoryItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface UsageDataPoint {
  date: string;
  query_count: number;
  total_tokens: number;
  total_cost: number;
}

// ─── Feedback ──────────────────────────────────────────────────────────────
export interface FeedbackRequest {
  query_id: string;
  feedback: -1 | 0 | 1;
}

// ─── API Keys ──────────────────────────────────────────────────────────────
export interface ApiKey {
  id: string;
  name: string;
  prefix: string;
  rate_limit: number;
  rate_window_seconds: number;
  scopes: string[] | null;
  expires_at: string | null;
  is_active: boolean;
  last_used_at: string | null;
  created_at: string;
}

export interface ApiKeyWithSecret extends ApiKey {
  api_key: string;
}

export interface ApiKeyCreateRequest {
  name: string;
  rate_limit?: number;
  rate_window_seconds?: number;
  scopes?: string[];
  expires_in_days?: number;
}
