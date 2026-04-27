from pydantic_settings import BaseSettings
from pathlib import Path


_PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    gemini_api_key: str = ""
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection_name: str = "media_embeddings"
    photos_dir: Path = _PROJECT_ROOT / "samplePhotos"
    vector_size: int = 3072

    class Config:
        env_prefix = ""
        extra = "ignore"


settings = Settings()
