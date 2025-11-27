from typing import Literal

from pydantic import BaseModel


class TextChunkResponse(BaseModel):

    type: Literal["text"]
    chunk: str | None
