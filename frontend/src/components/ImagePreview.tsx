import { SearchResult } from '../api';
import { photoUrl } from '../api';

interface ImagePreviewProps {
  result: SearchResult;
  onClose: () => void;
}

export default function ImagePreview({ result, onClose }: ImagePreviewProps) {
  return (
    <div
      className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="relative max-w-5xl max-h-full flex flex-col items-center"
        onClick={(e) => e.stopPropagation()}
      >
        <img
          src={photoUrl(result.file_path)}
          alt={result.file_name}
          className="max-w-full max-h-[80vh] object-contain rounded-lg"
        />
        <div className="mt-4 text-center text-gray-300">
          <p className="font-medium text-white">{result.file_name}</p>
          <p className="text-sm text-gray-400">
            Score: <span className="text-blue-300 font-mono">{result.score.toFixed(4)}</span>
            {result.width && result.height && (
              <span className="ml-3">{result.width} × {result.height}</span>
            )}
          </p>
          {(result.date_taken || result.location) && (
            <div className="mt-2 flex flex-col items-center gap-1">
              {result.date_taken && (
                <span className="text-xs text-gray-400">
                  {new Date(result.date_taken).toLocaleString(undefined, {
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </span>
              )}
              {result.location && (
                <span className="inline-flex items-center gap-1.5 text-xs text-emerald-400">
                  <svg className="h-4 w-4 flex-shrink-0" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                  <span>{result.location}</span>
                </span>
              )}
            </div>
          )}
          {result.labels && result.labels.length > 0 && (
            <div className="mt-2 flex flex-wrap justify-center gap-1.5">
              {result.labels.map((label) => (
                <span
                  key={label}
                  className="text-xs bg-gray-700 text-gray-300 px-2 py-0.5 rounded"
                >
                  {label}
                </span>
              ))}
            </div>
          )}
        </div>
        <button
          onClick={onClose}
          className="absolute top-0 right-0 -mt-2 -mr-2 bg-gray-800 hover:bg-gray-700 text-white rounded-full p-2 transition"
        >
          <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  );
}
