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
