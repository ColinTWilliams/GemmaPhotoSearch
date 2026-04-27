import logging
from pathlib import Path
from typing import List
from google import genai
from google.genai import types
from config import settings

logger = logging.getLogger(__name__)

MODEL = "gemini-embedding-2"
TASK = "SEMANTIC_SIMILARITY"


class GeminiEmbedder:
    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None:
            if not settings.gemini_api_key:
                raise ValueError("GEMINI_API_KEY is not set. Create a backend/.env file with GEMINI_API_KEY=your_key")
            self._client = genai.Client(api_key=settings.gemini_api_key)
        return self._client

    def embed_image(self, image_path: Path) -> List[float] | None:
        """Embed a single image file. Returns None on failure."""
        try:
            with open(image_path, "rb") as f:
                image_bytes = f.read()

            response = self.client.models.embed_content(
                model=MODEL,
                contents=[
                    types.Content(
                        parts=[
                            types.Part(
                                inline_data=types.Blob(
                                    data=image_bytes,
                                    mime_type="image/jpeg",
                                )
                            )
                        ]
                    )
                ],
                config=types.EmbedContentConfig(task_type=TASK),
            )
            # response.embeddings is a list of embeddings; take first
            embedding = response.embeddings[0]
            return list(embedding.values)
        except Exception as e:
            logger.error(f"Failed to embed image {image_path}: {e}")
            return None

    def embed_text(self, text: str) -> List[float] | None:
        """Embed a text query. Returns None on failure."""
        try:
            response = self.client.models.embed_content(
                model=MODEL,
                contents=[text],
                config=types.EmbedContentConfig(task_type=TASK),
            )
            embedding = response.embeddings[0]
            return list(embedding.values)
        except Exception as e:
            logger.error(f"Failed to embed text '{text}': {e}")
            return None
