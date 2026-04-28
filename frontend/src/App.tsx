import { useState, useEffect, useCallback } from 'react';
import SearchBar from './components/SearchBar';
import ResultsGrid from './components/ResultsGrid';
import ImagePreview from './components/ImagePreview';
import { search, indexPhotos, getStats, SearchResult } from './api';
import type { FilterState } from './components/SearchBar';

function App() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<SearchResult | null>(null);
  const [stats, setStats] = useState<{ total_indexed: number } | null>(null);
  const [indexing, setIndexing] = useState(false);
  const [threshold, setThreshold] = useState(0.3);

  useEffect(() => {
    getStats().then(setStats).catch(() => null);
    // Load all photos on initial mount (empty query browse mode)
    handleSearch('', { dateMin: '', dateMax: '', locationQuery: '' });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSearch = useCallback(async (q: string, filters: FilterState) => {
    setQuery(q);
    setLoading(true);
    setError(null);
    try {
      const data = await search(
        q,
        12,
        threshold,
        filters.dateMin || null,
        filters.dateMax || null,
        filters.locationQuery || null,
      );
      setResults(data.results);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Search failed');
    } finally {
      setLoading(false);
    }
  }, [threshold]);

  const handleIndex = async () => {
    setIndexing(true);
    setError(null);
    try {
      const data = await indexPhotos();
      const s = await getStats();
      setStats(s);
      alert(`Indexed ${data.indexed} new, updated ${data.updated} metadata, skipped ${data.skipped}, errors ${data.errors}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Index failed');
    } finally {
      setIndexing(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-gray-800 border-b border-gray-700 px-6 py-4 flex items-center justify-between sticky top-0 z-10">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-bold tracking-tight">GeminiPhotoSearch</h1>
          <span className="text-xs bg-blue-600 text-white px-2 py-0.5 rounded-full">
            Gemini Embedding 2
          </span>
        </div>
        <div className="flex items-center gap-3">
          {stats && (
            <span className="text-sm text-gray-400">
              {stats.total_indexed} indexed
            </span>
          )}
          <button
            onClick={handleIndex}
            disabled={indexing}
            className="text-sm bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white px-3 py-1.5 rounded-md transition"
          >
            {indexing ? 'Indexing...' : 'Re-index Photos'}
          </button>
        </div>
      </header>

      <main className="flex-1 px-6 py-8 max-w-7xl mx-auto w-full">
        <SearchBar
          onSearch={handleSearch}
          loading={loading}
          threshold={threshold}
          onThresholdChange={setThreshold}
        />

        {error && (
          <div className="mt-4 bg-red-900/40 border border-red-700 text-red-200 px-4 py-3 rounded-md">
            {error}
          </div>
        )}

        <ResultsGrid
          results={results}
          query={query}
          loading={loading}
          onPreview={setPreview}
        />
      </main>

      {preview && (
        <ImagePreview result={preview} onClose={() => setPreview(null)} />
      )}
    </div>
  );
}

export default App;
