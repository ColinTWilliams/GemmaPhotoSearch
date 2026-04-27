const API_BASE = '';

export interface SearchResult {
  id: string;
  score: number;
  file_path: string;
  file_name: string;
  media_type: string;
  width: number | null;
  height: number | null;
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

export async function search(query: string, top_k = 12): Promise<SearchResponse> {
  const res = await fetch(`${API_BASE}/api/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, top_k }),
  });
  if (!res.ok) throw new Error(`Search failed: ${res.statusText}`);
  return res.json();
}

export async function indexPhotos(): Promise<{ indexed: number; skipped: number; errors: number }> {
  const res = await fetch(`${API_BASE}/api/index`, { method: 'POST' });
  if (!res.ok) throw new Error(`Index failed: ${res.statusText}`);
  return res.json();
}

export async function getStats(): Promise<StatsResponse> {
  const res = await fetch(`${API_BASE}/api/stats`);
  if (!res.ok) throw new Error(`Stats failed: ${res.statusText}`);
  return res.json();
}

export function photoUrl(path: string): string {
  return `${API_BASE}/photos/${path}`;
}
