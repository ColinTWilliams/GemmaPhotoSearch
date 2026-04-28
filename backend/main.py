import logging
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from config import settings
from models.schemas import SearchRequest, SearchResponse, SearchResultItem, IndexResponse, StatsResponse
from services.gemini_embedder import GeminiEmbedder
from services.qdrant_store import QdrantStore
from services.indexer import Indexer
from services.docker_manager import start_qdrant_container

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Project root is two levels above this file (backend/main.py)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent

app = FastAPI(title="GeminiPhotoSearch", version="0.1.0")

# CORS for local React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_embedder = None
_store = None


@app.on_event("startup")
def startup():
    if not settings.gemini_api_key:
        logger.error("=" * 60)
        logger.error("GEMINI_API_KEY is not set!")
        logger.error("Set the environment variable: GEMINI_API_KEY=your_actual_key_here")
        logger.error("=" * 60)

    # Auto-start Qdrant Docker container if not already running
    started = start_qdrant_container(_PROJECT_ROOT)
    if not started:
        logger.warning(
            "Qdrant Docker auto-start failed. "
            "Ensure Docker Desktop is running, or Qdrant will fall back to in-memory mode."
        )

    # Eagerly initialize QdrantStore so connection failures surface at boot
    try:
        get_store()
    except ConnectionError as e:
        logger.error(str(e))
        raise


def get_embedder() -> GeminiEmbedder:
    global _embedder
    if _embedder is None:
        _embedder = GeminiEmbedder()
    return _embedder


def get_store() -> QdrantStore:
    global _store
    if _store is None:
        _store = QdrantStore()
    return _store


@app.post("/index", response_model=IndexResponse)
def index_photos():
    try:
        indexer = Indexer()
        result = indexer.index_photos()
        return IndexResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search", response_model=SearchResponse)
def search(request: SearchRequest):
    if request.query.strip():
        try:
            vector = get_embedder().embed_text(request.query)
        except ValueError as e:
            raise HTTPException(status_code=500, detail=str(e))

        if vector is None:
            raise HTTPException(status_code=502, detail="Embedding service failed")

        raw_results = get_store().hybrid_search(
            vector,
            top_k=request.top_k,
            score_threshold=request.score_threshold,
            date_min=request.date_min,
            date_max=request.date_max,
            location_query=request.location_query,
        )
    else:
        # Empty query: browse all photos sorted by date descending
        raw_results = get_store().scroll_all()
        raw_results.sort(
            key=lambda r: r.get("date_taken") or "",
            reverse=True,
        )
        for r in raw_results:
            r["score"] = 0.0

    results = [
        SearchResultItem(
            id=r["id"],
            score=r["score"],
            file_path=r["file_path"],
            file_name=r["file_name"],
            media_type=r["media_type"],
            width=r.get("width"),
            height=r.get("height"),
            labels=r.get("labels"),
            date_taken=r.get("date_taken"),
            location=r.get("location"),
            lat=r.get("lat"),
            lon=r.get("lon"),
        )
        for r in raw_results
    ]
    return SearchResponse(results=results, query=request.query, total=len(results))


@app.get("/photos/{path:path}")
def serve_photo(path: str):
    # Security: ensure the resolved path stays within photos_dir
    base = settings.photos_dir.resolve()
    target = (base / path).resolve()
    if not str(target).startswith(str(base)):
        raise HTTPException(status_code=403, detail="Access denied")
    if not target.exists():
        raise HTTPException(status_code=404, detail="File not found")

    mime_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
    }
    media_type = mime_types.get(target.suffix.lower(), "application/octet-stream")

    def file_stream():
        with open(target, "rb") as f:
            while chunk := f.read(8192):
                yield chunk

    return StreamingResponse(file_stream(), media_type=media_type)


@app.get("/stats", response_model=StatsResponse)
def stats():
    s = get_store()
    return StatsResponse(
        total_indexed=s.count(),
        collection_name=settings.qdrant_collection_name,
        vector_size=settings.vector_size,
    )
