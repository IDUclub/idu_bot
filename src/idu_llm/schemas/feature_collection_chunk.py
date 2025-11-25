from typing import Literal

from pydantic import BaseModel


# TODO add FeatureCollection validation
class FeatureCollectionChunk(BaseModel):

    type: Literal["feature_collections"]
    chunk: dict
