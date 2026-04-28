import hashlib
import logging
import uuid
from pathlib import Path
from typing import List, Tuple
from PIL import Image
from qdrant_client.models import PointStruct
from services.gemini_embedder import GeminiEmbedder, DEFAULT_LABELS
from services.qdrant_store import QdrantStore
from services.metadata_extractor import extract_metadata
from config import settings

logger = logging.getLogger(__name__)

SUPPORTED_IMAGE_TYPES = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}


class Indexer:
    def __init__(self):
        self.embedder = GeminiEmbedder()
        self.store = QdrantStore()

    def _compute_hash(self, path: Path) -> str:
        hasher = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _hash_to_uuid(self, hex_hash: str) -> uuid.UUID:
        # Deterministic UUID from first 16 bytes of SHA256 hash
        return uuid.UUID(bytes=bytes.fromhex(hex_hash[:32]))

    def _get_image_dimensions(self, path: Path) -> Tuple[int, int]:
        try:
            with Image.open(path) as img:
                return img.size
        except Exception:
            return (0, 0)

    def _has_metadata(self, payload: dict) -> bool:
        """Check if payload already has extracted metadata."""
        return payload.get("date_taken") is not None or payload.get("location") is not None

    def index_photos(self) -> dict:
        photos_dir = settings.photos_dir.resolve()
        if not photos_dir.exists():
            raise FileNotFoundError(f"Photos directory not found: {photos_dir}")

        # Embed the default label vocabulary once
        label_vectors = self.embedder.embed_labels(DEFAULT_LABELS)
        logger.info(f"Embedded {len(label_vectors)} label vectors for label matching")

        # Build a map of existing hashes -> point info (id, payload, vector)
        existing_by_hash: dict[str, dict] = {}
        offset = 0
        while True:
            response = self.store.client.scroll(
                collection_name=self.store.collection_name,
                offset=offset,
                limit=100,
                with_payload=True,
                with_vectors=True,
            )
            points = response[0] if isinstance(response, tuple) else response
            if not points:
                break
            for p in points:
                h = p.payload.get("content_hash")
                if h:
                    existing_by_hash[h] = {
                        "id": p.id,
                        "payload": p.payload,
                        "vector": p.vector,
                    }
            offset += len(points)

        indexed = 0
        updated = 0
        skipped = 0
        errors = 0
        new_points: List[PointStruct] = []
        update_points: List[PointStruct] = []

        for file_path in photos_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_IMAGE_TYPES:
                file_hash = self._compute_hash(file_path)
                existing = existing_by_hash.get(file_hash)

                if existing:
                    # File already indexed — check if metadata is missing
                    if self._has_metadata(existing["payload"]):
                        skipped += 1
                        continue
                    # Update with metadata only (no re-embedding)
                    meta = extract_metadata(file_path)
                    if meta.get("date_taken") or meta.get("location"):
                        existing["payload"]["date_taken"] = meta.get("date_taken")
                        existing["payload"]["location"] = meta.get("location")
                        existing["payload"]["lat"] = meta.get("lat")
                        existing["payload"]["lon"] = meta.get("lon")
                        update_points.append(
                            PointStruct(id=existing["id"], vector=existing["vector"], payload=existing["payload"])
                        )
                        updated += 1
                        logger.info(f"Updated metadata for {file_path.name}: {meta.get('location')}")
                    else:
                        skipped += 1
                    continue

                # Brand new file — full embed pipeline
                vector = self.embedder.embed_image(file_path)
                if vector is None:
                    errors += 1
                    continue

                labels = self.embedder.compute_label_similarities(vector, label_vectors, top_n=5)
                width, height = self._get_image_dimensions(file_path)
                meta = extract_metadata(file_path)
                payload = {
                    "file_path": str(file_path.relative_to(settings.photos_dir)).replace("\\", "/"),
                    "file_name": file_path.name,
                    "media_type": "image",
                    "width": width,
                    "height": height,
                    "content_hash": file_hash,
                    "labels": labels,
                    "date_taken": meta.get("date_taken"),
                    "location": meta.get("location"),
                    "lat": meta.get("lat"),
                    "lon": meta.get("lon"),
                }

                point_id = self._hash_to_uuid(file_hash)
                new_points.append(
                    PointStruct(id=point_id, vector=vector, payload=payload)
                )
                indexed += 1

        if new_points:
            self.store.upsert(new_points)
        if update_points:
            self.store.upsert(update_points)

        logger.info(f"Indexing complete: {indexed} new, {updated} updated, {skipped} skipped, {errors} errors")
        return {"indexed": indexed, "updated": updated, "skipped": skipped, "errors": errors}
