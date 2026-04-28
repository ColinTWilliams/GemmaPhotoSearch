from pydantic import BaseModel
from typing import List


class SearchRequest(BaseModel):
    query: str
    top_k: int = 12
    score_threshold: float = 0.3


class SearchResultItem(BaseModel):
    id: str
    score: float
    file_path: str
    file_name: str
    media_type: str
    width: int | None = None
    height: int | None = None
    labels: List[str] | None = None


class SearchResponse(BaseModel):
    results: List[SearchResultItem]
    query: str
    total: int


class IndexResponse(BaseModel):
    indexed: int
    skipped: int
    errors: int


class StatsResponse(BaseModel):
    total_indexed: int
    collection_name: str
    vector_size: int
