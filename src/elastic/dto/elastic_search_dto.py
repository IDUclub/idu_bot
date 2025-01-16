from pydantic import BaseModel, Field


class ElasticSearchDTO(BaseModel):
    prompt: str = Field(description="search prompt")
