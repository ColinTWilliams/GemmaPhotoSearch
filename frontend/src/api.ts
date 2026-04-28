const API_BASE = '';

export interface SearchResult {
  id: string;
  score: number;
  file_path: string;
  file_name: string;
  media_type: string;
  width: number | null;
  height: number | null;
  labels: string[] | null;
}

export interface SearchResponse {
  results: SearchResult[];
  query: string;
  total: number;
}

export interface StatsResponse {
  total_indexed: number;
  collection_name: string;
  vector_size: number;
}

async function handleResponse<T>(res: Response, action: string): Promise<T> {
  if (!res.ok) {
    let message = res.statusText;
    try {
      const body = await res.json();
      if (body.detail) message = body.detail;
    } catch {
      // ignore parse errors
    }
    throw new Error(`${action} failed: ${message}`);
  }
  return res.json();
}

export async function search(query: string, top_k = 12, score_threshold = 0.3): Promise<SearchResponse> {
  const res = await fetch(`${API_BASE}/api/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, top_k, score_threshold }),
  });
  return handleResponse(res, 'Search');
}

export async function indexPhotos(): Promise<{ indexed: number; skipped: number; errors: number }> {
  const res = await fetch(`${API_BASE}/api/index`, { method: 'POST' });
  return handleResponse(res, 'Index');
}

export async function getStats(): Promise<StatsResponse> {
  const res = await fetch(`${API_BASE}/api/stats`);
  return handleResponse(res, 'Stats');
}

export function photoUrl(path: string): string {
  return `${API_BASE}/photos/${path}`;
}
