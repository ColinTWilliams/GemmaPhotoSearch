import { SearchResult } from '../api';
import { photoUrl } from '../api';

interface ResultsGridProps {
  results: SearchResult[];
  query: string;
  loading: boolean;
  onPreview: (result: SearchResult) => void;
}

export default function ResultsGrid({ results, query, loading, onPreview }: ResultsGridProps) {
  if (!query && !loading) {
    return (
      <div className="mt-12 text-center text-gray-500">
        <p className="text-lg">Type a query above to search your photos</p>
      </div>
    );
  }

  if (!loading && results.length === 0 && query) {
    return (
      <div className="mt-12 text-center text-gray-500">
        <p className="text-lg">No matches found for "{query}"</p>
      </div>
    );
  }

  return (
    <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
      {results.map((r) => (
        <button
          key={r.id}
          onClick={() => onPreview(r)}
          className="group relative bg-gray-800 rounded-xl overflow-hidden border border-gray-700 hover:border-gray-500 transition text-left"
        >
          <div className="aspect-[4/3] w-full overflow-hidden">
            <img
              src={photoUrl(r.file_path)}
              alt={r.file_name}
              loading="lazy"
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
            />
          </div>
          <div className="p-3 flex items-center justify-between">
            <span className="text-sm text-gray-300 truncate max-w-[70%]" title={r.file_name}>
              {r.file_name}
            </span>
            <span className="text-xs bg-blue-900/60 text-blue-200 px-2 py-0.5 rounded-full font-mono">
              {r.score.toFixed(3)}
            </span>
          </div>
        </button>
      ))}
    </div>
  );
}
