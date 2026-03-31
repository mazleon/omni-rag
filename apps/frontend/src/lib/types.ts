export interface Document {
  id: string;
  organization_id: string;
  filename: string;
  file_size_bytes: number | null;
  mime_type: string | null;
  status: "pending" | "processing" | "indexed" | "error";
  error_message: string | null;
  created_at: string;
  updated_at: string;
  metadata?: Record<string, any>;
}

export interface UploadRequest {
  filename: string;
  mime_type: string;
  file_size_bytes: number;
}

export interface UploadResponse {
  document_id: string;
  presigned_url: string;
}

export interface Citation {
  chunk_id: string;
  document_id: string;
  document_title: string;
  page_number?: number;
  relevance_score: number;
  excerpt: string;
}
