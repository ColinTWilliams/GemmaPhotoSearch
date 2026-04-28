import logging
from pathlib import Path
from typing import List, Dict
from google import genai
from google.genai import types
from config import settings

logger = logging.getLogger(__name__)

MODEL = "gemini-embedding-2"
TASK = "SEMANTIC_SIMILARITY"

DEFAULT_LABELS = [
    "person", "woman", "man", "child", "baby", "crowd", "face", "portrait",
    "dog", "cat", "bird", "horse", "deer", "bear", "fish", "insect", "butterfly",
    "tree", "forest", "mountain", "ocean", "beach", "river", "lake", "waterfall",
    "sky", "cloud", "sunset", "sunrise", "rainbow", "storm", "snow", "flower", "grass",
    "car", "truck", "bus", "bicycle", "motorcycle", "boat", "ship", "airplane", "train",
    "building", "house", "skyscraper", "bridge", "road", "street", "highway",
    "food", "fruit", "vegetable", "pizza", "cake", "coffee", "drink",
    "chair", "table", "furniture", "bed", "door", "window", "stairs",
    "phone", "computer", "laptop", "camera", "watch", "clock", "television",
    "book", "painting", "sculpture", "musical instrument", "guitar", "piano",
    "ball", "sports", "running", "swimming", "hiking", "cycling", "skiing",
    "park", "garden", "city", "downtown", "market", "store", "restaurant",
    "kitchen", "bedroom", "bathroom", "living room", "office", "classroom",
    "wedding", "party", "concert", "festival", "meeting", "ceremony",
    "indoor", "outdoor", "daytime", "nighttime", "sunny", "cloudy", "rainy",
    "red", "blue", "green", "yellow", "orange", "purple", "pink", "black", "white", "brown", "gray",
    "macro", "close-up", "landscape", "aerial", "panoramic", "blurry",
]


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

    def embed_labels(self, labels: List[str]) -> Dict[str, List[float]]:
        """Embed a batch of labels. Returns {label: vector}."""
        result: Dict[str, List[float]] = {}
        # Batch them to reduce API calls
        for label in labels:
            vector = self.embed_text(label)
            if vector is not None:
                result[label] = vector
        return result

    def compute_label_similarities(self, image_vector: List[float], label_vectors: Dict[str, List[float]], top_n: int = 5) -> List[str]:
        """Find the top-N most similar labels for a given image vector using cosine similarity."""
        if not label_vectors:
            return []

        # Cosine similarity = dot product of unit vectors
        import math

        def norm(v):
            return math.sqrt(sum(x * x for x in v))

        img_norm = norm(image_vector)
        if img_norm == 0:
            return []

        scores = []
        for label, vector in label_vectors.items():
            vec_norm = norm(vector)
            if vec_norm == 0:
                continue
            dot = sum(a * b for a, b in zip(image_vector, vector))
            similarity = dot / (img_norm * vec_norm)
            scores.append((label, similarity))

        scores.sort(key=lambda x: x[1], reverse=True)
        return [label for label, _ in scores[:top_n]]
