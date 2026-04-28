import { useState, useRef, useEffect } from 'react';

export interface FilterState {
  dateMin: string;
  dateMax: string;
  locationQuery: string;
}

interface SearchBarProps {
  onSearch: (query: string, filters: FilterState) => void;
  loading: boolean;
  threshold: number;
  onThresholdChange: (value: number) => void;
}

export default function SearchBar({ onSearch, loading, threshold, onThresholdChange }: SearchBarProps) {
  const [input, setInput] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [dateMin, setDateMin] = useState('');
  const [dateMax, setDateMax] = useState('');
  const [locationQuery, setLocationQuery] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSearch(input, { dateMin, dateMax, locationQuery });
  };

  const today = new Date().toISOString().split('T')[0];

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-2xl mx-auto">
      <div className="relative">
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Search your photos with natural language..."
          className="w-full bg-gray-800 border border-gray-700 rounded-xl px-5 py-4 pr-14 text-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="absolute right-3 top-1/2 -translate-y-1/2 bg-blue-600 hover:bg-blue-700 disabled:opacity-40 disabled:hover:bg-blue-600 text-white p-2 rounded-lg transition"
        >
          {loading ? (
            <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
          ) : (
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          )}
        </button>
      </div>

      <div className="mt-3 flex items-center justify-center gap-3">
        <span className="text-xs text-gray-400">Threshold</span>
        <input
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={threshold}
          onChange={(e) => onThresholdChange(parseFloat(e.target.value))}
          className="w-32 accent-blue-500"
        />
        <span className="text-xs font-mono text-blue-300 w-10 text-right">{threshold.toFixed(2)}</span>
        <button
          type="button"
          onClick={() => setShowFilters((v) => !v)}
          className="text-xs text-blue-400 hover:text-blue-300 underline ml-2"
        >
          {showFilters ? 'Hide filters' : 'Filters'}
        </button>
      </div>

      {showFilters && (
        <div className="mt-3 bg-gray-800 border border-gray-700 rounded-lg p-4 space-y-3">
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="flex-1">
              <label className="block text-xs text-gray-400 mb-1">From date</label>
              <input
                type="date"
                max={today}
                value={dateMin}
                onChange={(e) => setDateMin(e.target.value)}
                className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            <div className="flex-1">
              <label className="block text-xs text-gray-400 mb-1">To date</label>
              <input
                type="date"
                max={today}
                value={dateMax}
                onChange={(e) => setDateMax(e.target.value)}
                className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Location</label>
            <input
              type="text"
              value={locationQuery}
              onChange={(e) => setLocationQuery(e.target.value)}
              placeholder="e.g. Monroe Street, Madison"
              className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm text-white placeholder-gray-600 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
        </div>
      )}

      <p className="text-center text-sm text-gray-500 mt-2">
        Try: "dog at the park", "autumn leaves", "family portrait"
      </p>
    </form>
  );
}
