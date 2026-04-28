# Agent Rules & Memories — GeminiPhotoSearch

## Workflow Rules
1. **Commit Before Big Changes** — When the working tree has uncommitted changes and a new multi-file feature is about to be implemented, ALWAYS commit/push existing work first before starting the new work. The user explicitly requested this.
2. **Never Commit Secrets** — `.env`, API keys, `samplePhotos/`, `node_modules/`, and `qdrant_storage/` are all gitignored. Always verify `git diff --cached` before committing to ensure no secrets slip in.

## Project Context
- Embedding API: Google Gemini Embedding 2 (`google-genai` SDK)
- Vector DB: Qdrant (Docker via `docker-compose.yml`, with in-memory fallback)
- Backend: FastAPI + Uvicorn, Python 3.12+
- Frontend: React 19 + Vite + Tailwind CSS
- Photos directory: `samplePhotos/` (gitignored, never commit personal media)
- Docker manager (`backend/services/docker_manager.py`) auto-starts Qdrant container on backend startup if Docker is available.

## Architecture Decisions (Locked)
- Qdrant point IDs are deterministic UUIDs derived from SHA256 content hash (first 16 bytes), not random UUIDs. This enables idempotent re-indexing.
- Label similarity uses cosine similarity against a pre-computed vocabulary of ~100 labels, giving each photo 5 semantic tags.
- Search is a hybrid OR: semantic vector search + metadata fuzzy matching (location, date). Results are deduplicated and merged.
- Reverse geocoding uses Nominatim (OpenStreetMap) with a local SQLite cache to avoid repeated API calls for the same coordinates.
