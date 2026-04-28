import difflib
import logging
import time
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, Range, MatchValue
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

    def hybrid_search(
        self,
        vector: List[float],
        top_k: int = 12,
        score_threshold: float = 0.3,
        date_min: str | None = None,
        date_max: str | None = None,
        location_query: str | None = None,
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search: semantic vector search OR metadata fuzzy matching.
        Returns deduplicated, sorted results.
        """
        # --- Semantic leg (vector search) ---
        semantic_results = self.search(vector, top_k=top_k * 4, score_threshold=score_threshold)

        # --- Metadata leg ---
        metadata_results: List[Dict[str, Any]] = []
        need_metadata = bool(location_query or date_min or date_max)

        if need_metadata:
            # Build Qdrant date filter if dates are provided
            qdrant_filter = None
            if date_min or date_max:
                conditions = []
                if date_min:
                    conditions.append(
                        FieldCondition(key="date_taken", range=Range(gte=date_min))
                    )
                if date_max:
                    conditions.append(
                        FieldCondition(key="date_taken", range=Range(lte=date_max))
                    )
                qdrant_filter = Filter(must=conditions)

            # Scroll through all points (or filtered subset if dates)
            candidates = self.client.scroll(
                collection_name=self.collection_name,
                limit=1000,
                offset=0,
                with_payload=True,
                with_vectors=False,
                scroll_filter=qdrant_filter,
            )
            if isinstance(candidates, tuple):
                candidate_points = candidates[0]
            else:
                candidate_points = candidates

            location_lower = (location_query or "").strip().lower()
            for p in candidate_points:
                payload = p.payload
                # Date check already handled by Qdrant filter if provided
                # Location fuzzy match
                matched = False
                if location_lower:
                    loc = (payload.get("location") or "").lower()
                    # difflib ratio threshold 0.4 gives reasonable fuzzy matching
                    if location_lower in loc:
                        matched = True
                    elif loc and difflib.SequenceMatcher(None, location_lower, loc).ratio() > 0.4:
                        matched = True
                else:
                    # If only date filters, all returned candidates match
                    matched = True

                if matched:
                    metadata_results.append({
                        "id": str(p.id),
                        "score": 0.95,  # synthetic score for metadata matches
                        **payload,
                    })

        # --- Merge & deduplicate ---
        seen = set()
        merged: List[Dict[str, Any]] = []
        for r in semantic_results:
            if r["id"] not in seen:
                seen.add(r["id"])
                merged.append(r)
        for r in metadata_results:
            if r["id"] not in seen:
                seen.add(r["id"])
                merged.append(r)

        # Sort by score descending
        merged.sort(key=lambda x: x["score"], reverse=True)
        return merged[:top_k]

    def count(self) -> int:
        return self.client.count(collection_name=self.collection_name).count

    def scroll_all(self) -> List[Dict[str, Any]]:
        """Return all points with payload (no vectors)."""
        all_points: List[Dict[str, Any]] = []
        offset = 0
        while True:
            response = self.client.scroll(
                collection_name=self.collection_name,
                offset=offset,
                limit=100,
                with_payload=True,
                with_vectors=False,
            )
            if isinstance(response, tuple):
                points = response[0]
            else:
                points = response
            if not points:
                break
            for p in points:
                all_points.append({"id": str(p.id), **p.payload})
            offset += len(points)
        return all_points

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
