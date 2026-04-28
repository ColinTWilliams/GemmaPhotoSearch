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
          <div className="p-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-300 truncate max-w-[70%]" title={r.file_name}>
                {r.file_name}
              </span>
              <span className="text-xs bg-blue-900/60 text-blue-200 px-2 py-0.5 rounded-full font-mono">
                {r.score.toFixed(3)}
              </span>
            </div>
            {(r.date_taken || r.location) && (
              <div className="mt-1.5 flex flex-col gap-1">
                {r.date_taken && (
                  <span className="text-[10px] text-gray-400 leading-tight">
                    {new Date(r.date_taken).toLocaleDateString()}
                  </span>
                )}
                {r.location && (
                  <span className="inline-flex items-center gap-1 text-[10px] text-emerald-400 leading-tight">
                    <svg className="h-3 w-3 flex-shrink-0" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                    <span className="truncate max-w-full" title={r.location}>{r.location}</span>
                  </span>
                )}
              </div>
            )}
            {r.labels && r.labels.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {r.labels.map((label) => (
                  <span
                    key={label}
                    className="text-xs bg-gray-700 text-gray-300 px-1.5 py-0.5 rounded"
                  >
                    {label}
                  </span>
                ))}
              </div>
            )}
          </div>
        </button>
      ))}
    </div>
  );
}
