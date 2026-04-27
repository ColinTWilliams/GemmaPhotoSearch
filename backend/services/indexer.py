import hashlib
import logging
import uuid
from pathlib import Path
from typing import List, Tuple
from PIL import Image
from qdrant_client.models import PointStruct
from services.gemini_embedder import GeminiEmbedder
from services.qdrant_store import QdrantStore
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

    def index_photos(self) -> dict:
        photos_dir = settings.photos_dir.resolve()
        if not photos_dir.exists():
            raise FileNotFoundError(f"Photos directory not found: {photos_dir}")

        # Build a map of existing IDs to content hashes to skip re-indexing
        existing_ids = self.store.get_all_ids()
        existing_hashes = set()
        if existing_ids:
            # Retrieve payloads for existing IDs to get content_hash
            offset = 0
            while True:
                response = self.store.client.scroll(
                    collection_name=self.store.collection_name,
                    offset=offset,
                    limit=100,
                    with_payload=True,
                    with_vectors=False,
                )
                points = response[0]
                if not points:
                    break
                for p in points:
                    h = p.payload.get("content_hash")
                    if h:
                        existing_hashes.add(h)
                offset += len(points)

        indexed = 0
        skipped = 0
        errors = 0
        points: List[PointStruct] = []

        for file_path in photos_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_IMAGE_TYPES:
                file_hash = self._compute_hash(file_path)
                if file_hash in existing_hashes:
                    skipped += 1
                    continue

                vector = self.embedder.embed_image(file_path)
                if vector is None:
                    errors += 1
                    continue

                width, height = self._get_image_dimensions(file_path)
                payload = {
                    "file_path": str(file_path.relative_to(Path("..").resolve())),
                    "file_name": file_path.name,
                    "media_type": "image",
                    "width": width,
                    "height": height,
                    "content_hash": file_hash,
                }

                point_id = self._hash_to_uuid(file_hash)
                points.append(
                    PointStruct(id=point_id, vector=vector, payload=payload)
                )
                indexed += 1

        if points:
            self.store.upsert(points)

        logger.info(f"Indexing complete: {indexed} new, {skipped} skipped, {errors} errors")
        return {"indexed": indexed, "skipped": skipped, "errors": errors}
