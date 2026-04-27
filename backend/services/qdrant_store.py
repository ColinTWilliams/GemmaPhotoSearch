import logging
from pathlib import Path
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Payload
from config import settings

logger = logging.getLogger(__name__)


class QdrantStore:
    def __init__(self):
        # In-memory mode avoids Windows file-locking issues with uvicorn --reload
        self.client = QdrantClient(":memory:")
        self.collection_name = settings.qdrant_collection_name
        self._ensure_collection()

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

    def search(self, vector: List[float], top_k: int = 12) -> List[Dict[str, Any]]:
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=vector,
            limit=top_k,
            with_payload=True,
        )
        return [
            {
                "id": r.id,
                "score": r.score,
                **r.payload,
            }
            for r in results
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
            points = response[0]
            if not points:
                break
            all_ids.update(p.id for p in points)
            offset += len(points)
        return all_ids
