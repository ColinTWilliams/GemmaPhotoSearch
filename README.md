# GeminiPhotoSearch

A web-based multimodal semantic search app for your local photo library, powered by **Google Gemini Embedding 2**.

Type natural language queries like "dog at the park" or "autumn leaves" and see your photos ranked by semantic similarity — no manual tagging required.

## Features

- **Text-to-image search**: Type any description and find matching photos via multimodal embeddings.
- **Gemini Embedding 2**: Uses Google's first natively multimodal embedding model (text, image, video, audio, documents in one unified space).
- **Qdrant vector database**: Persistent vector storage with cosine similarity search (runs in Docker).
- **React + Tailwind UI**: Clean, responsive dark-mode interface with image previews.
- **Extensible**: Ready to add PDFs, videos, and audio later — same vector space, same search.

## Architecture

```
React Frontend  <--HTTP-->  FastAPI Backend  <--API-->  Gemini Embedding 2
     |                            |
     |                            v
     v                        Qdrant (Docker)
Image preview            Persistent vector storage + search
```

## Quick Start

### 1. Prerequisites

- Python 3.12+
- Node.js 20+
- Docker Desktop (for Qdrant persistence)
- A [Gemini API key](https://ai.google.dev/gemini-api/docs/api-key) (free tier available)

### 2. Clone & Setup

```bash
git clone https://github.com/ColinTWilliams/GeminiPhotoSearch.git
cd GeminiPhotoSearch
```

### 3. Add your photos

Place your images in the `samplePhotos/` directory (already `.gitignore`-d so they won't be committed):

```bash
# On Windows, just copy files into samplePhotos/
# Supported: .jpg, .jpeg, .png, .webp, .gif, .bmp
```

### 4. Backend Setup

```bash
cd backend
python -m venv .venv

# Windows PowerShell
.venv\Scripts\python.exe -m pip install -r requirements.txt

# Set your API key as an environment variable
# (PowerShell)
$env:GEMINI_API_KEY="your_actual_key_here"

# Start the server
.venv\Scripts\uvicorn.exe main:app --reload --port 8000
```

The backend will automatically start the Qdrant Docker container on startup if Docker Desktop is running. If Docker isn't available, it gracefully falls back to in-memory mode (data won't persist across restarts).

### 5. Frontend Setup

In a **new terminal**:

```bash
cd frontend
npm install
npm run dev
```

The frontend will open at **http://localhost:5173** and proxy API calls to the backend.

### 6. First Index

1. Open the web app.
2. Click **"Re-index Photos"** in the top right.
3. Wait while Gemini Embedding 2 generates vectors for each image.
4. Start typing queries like "dog running" or "sunny day".

## Project Structure

```
GeminiPhotoSearch/
├── backend/
│   ├── main.py                  # FastAPI app (search, index, stats, photo serving)
│   ├── config.py                # Pydantic settings + .env loader
│   ├── models/schemas.py        # Request/response Pydantic models
│   ├── services/
│   │   ├── gemini_embedder.py   # Google genai SDK wrapper
│   │   ├── qdrant_store.py      # Qdrant local vector DB client
│   │   └── indexer.py           # Photo scan + embed + upsert pipeline
│   ├── requirements.txt
│   └── .env.example             # Template for your API key
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # Main app shell
│   │   ├── api.ts               # Fetch wrappers for backend APIs
│   │   └── components/
│   │       ├── SearchBar.tsx
│   │       ├── ResultsGrid.tsx
│   │       └── ImagePreview.tsx
│   ├── package.json
│   └── vite.config.ts         # Dev proxy to backend
├── samplePhotos/                # Your images (gitignored)
├── .gitignore                   # Excludes .env, samplePhotos, venvs
└── README.md
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/index` | Scan `samplePhotos/`, embed new/changed images, upsert to Qdrant |
| `POST` | `/search` | `{ "query": "dog park", "top_k": 12 }` — returns ranked results |
| `GET`  | `/photos/{path}` | Serve original image file for browser preview |
| `GET`  | `/stats` | Indexed count, collection name, vector size |

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Embedding API | `google-genai` + `gemini-embedding-2` | GA April 2026; natively multimodal; 3072-dim unified space |
| Vector DB | Qdrant (Docker) | Persistent, file-lock-free, schemaless payloads |
| Backend | FastAPI + Uvicorn | Async-native, auto OpenAPI docs, easy file streaming |
| Frontend | React 19 + Vite + TypeScript + Tailwind CSS | Fast HMR, type safety, modern DX |

## Extending to Non-Photo Files

Gemini Embedding 2 embeds **text, images, video, audio, and documents** into the same vector space. To add support later:

1. Update `indexer.py` to detect `.pdf`, `.mp4`, `.mp3` files.
2. Pass file bytes to `embed_content()` with the appropriate MIME type.
3. Set `media_type` in the Qdrant payload.
4. Frontend switches preview component based on `media_type` (video player, PDF iframe, etc.).

No database migration needed — Qdrant payloads are schemaless.

## Security Notes

- `GEMINI_API_KEY` is read from the **environment variable** `GEMINI_API_KEY`.
- `samplePhotos/` is also `.gitignore`-d so your personal media is never committed.
- The `/photos/{path}` endpoint validates paths to prevent directory traversal.
- The frontend proxy configuration never exposes the API key to the browser.

## License

MIT
