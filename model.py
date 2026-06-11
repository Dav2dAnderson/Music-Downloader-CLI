from pydantic import BaseModel
from typing import List


class AudioTrack(BaseModel):
    preview_url: str
    url: str | None = None

    name: str
    author: str

    duration: int | None = None


class SearchResult(BaseModel):
    tracks: List[AudioTrack]
    total: int
    page: int
    limit: int
    has_next: bool