from pydantic import BaseModel


class AudioTrack(BaseModel):
    preview_url: str
    url: str | None = None

    name: str
    author: str

    duration: int | None = None