import logging
import time
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from config import settings

logger = logging.getLogger(__name__)

_RETRIES = 5
_RETRY_DELAY = 2.0


class QdrantStore:
    """Singleton Qdrant store — shared across indexer and search endpoints."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.collection_name = settings.qdrant_collection_name
        if settings.qdrant_mode == "memory":
            logger.info("Qdrant mode=memory; using in-memory store.")
            self.client = QdrantClient(":memory:")
            self._ensure_collection()
            self._initialized = True
            return
        client = self._connect_with_retry()
        if client is not None:
            self.client = client
            self._ensure_collection()
            logger.info(f"Connected to Qdrant at {settings.qdrant_host}:{settings.qdrant_port}")
        else:
            if settings.qdrant_mode == "docker":
                raise ConnectionError(
                    f"Could not connect to Qdrant at {settings.qdrant_host}:{settings.qdrant_port} "
                    f"after {_RETRIES} attempts. "
                    "Set QDRANT_MODE=auto to allow in-memory fallback, or ensure Qdrant is running."
                )
            logger.error(
                "Could not connect to Qdrant server after %d attempts; falling back to in-memory mode. "
                "Indexed data will NOT persist across restarts.",
                _RETRIES,
            )
            self.client = QdrantClient(":memory:")
            self._ensure_collection()
        self._initialized = True

    def _connect_with_retry(self):
        for attempt in range(1, _RETRIES + 1):
            try:
                client = QdrantClient(
                    host=settings.qdrant_host,
                    port=settings.qdrant_port,
                )
                client.get_collections()
                return client
            except Exception as e:
                logger.debug("Qdrant connection attempt %d/%d failed: %s", attempt, _RETRIES, e)
                if attempt < _RETRIES:
                    time.sleep(_RETRY_DELAY)
        return None

    def _ensure_collection(self):
        collections = self.client.get_collections().collections
        names = [c.name for c in collections]
        if self.collection_name not in names:
            logger.info(f"Creating collection '{self.collection_name}' with size {settings.vector_size}")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=settings.vector_size, distance=Distance.COSINE),
            )

    def upsert(self, points: List[PointStruct]):
        if not points:
            return
        self.client.upsert(collection_name=self.collection_name, points=points)

    def search(self, vector: List[float], top_k: int = 12, score_threshold: float = 0.3) -> List[Dict[str, Any]]:
        response = self.client.query_points(
            collection_name=self.collection_name,
            query=vector,
            limit=top_k,
            score_threshold=score_threshold,
            with_payload=True,
        )
        return [
            {
                "id": str(p.id),
                "score": p.score,
                **p.payload,
            }
            for p in response.points
        ]

    def count(self) -> int:
        return self.client.count(collection_name=self.collection_name).count

    def get_all_ids(self) -> set:
        """Return all point IDs currently in the collection."""
        all_ids = set()
        offset = 0
        while True:
            response = self.client.scroll(
                collection_name=self.collection_name,
                offset=offset,
                limit=100,
                with_payload=False,
                with_vectors=False,
            )
            # QdrantLocal.scroll returns a tuple: (points, next_offset)
            if isinstance(response, tuple):
                points = response[0]
            else:
                points = response
            if not points:
                break
            all_ids.update(str(p.id) for p in points)
            offset += len(points)
        return all_ids
