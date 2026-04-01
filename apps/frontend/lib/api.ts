const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/v1';

export interface Document {
  id: string;
  filename: string;
  status: string;
  num_chunks: number | null;
  created_at: string;
}

export interface DocumentUploadResponse {
  document_id: string;
  upload_url: string;
  status: string;
}

export interface QuerySource {
  chunk_id: string;
  document_id: string;
  content: string;
  page_numbers: number[] | null;
  score: number;
}

export interface QueryResponse {
  answer: string;
  sources: QuerySource[];
  latency_ms: number;
  tokens_used: number | null;
}

export interface DocumentStatus {
  document_id: string;
  status: string;
  num_chunks: number | null;
  error: string | null;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_URL) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  async uploadDocument(
    file: File,
    collectionId?: string
  ): Promise<DocumentUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    if (collectionId) {
      formData.append('collection_id', collectionId);
    }

    const response = await fetch(`${this.baseUrl}/documents/upload`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(error.detail || 'Upload failed');
    }

    return response.json();
  }

  async getDocumentStatus(documentId: string): Promise<DocumentStatus> {
    return this.request(`/documents/${documentId}/status`);
  }

  async listDocuments(
    collectionId?: string,
    limit: number = 50,
    offset: number = 0
  ): Promise<Document[]> {
    const params = new URLSearchParams({
      limit: limit.toString(),
      offset: offset.toString(),
    });
    if (collectionId) {
      params.append('collection_id', collectionId);
    }
    return this.request(`/documents?${params}`);
  }

  async query(query: string, collectionId?: string): Promise<QueryResponse> {
    return this.request('/query', {
      method: 'POST',
      body: JSON.stringify({ query, collection_id: collectionId }),
    });
  }

  async queryStream(
    query: string,
    collectionId?: string,
    onChunk: (data: any) => void
  ): Promise<void> {
    const response = await fetch(`${this.baseUrl}/query/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, collection_id: collectionId }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Query failed' }));
      throw new Error(error.detail || 'Query failed');
    }

    const reader = response.body?.getReader();
    if (!reader) throw new Error('No response body');

    const decoder = new TextDecoder();
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const text = decoder.decode(value);
      const lines = text.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            onChunk(data);
          } catch {
            // Skip invalid JSON
          }
        }
      }
    }
  }
}

export const api = new ApiClient();
export default api;