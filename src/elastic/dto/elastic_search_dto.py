from pydantic import BaseModel, Field


class ElasticSearchDTO(BaseModel):

    prompt: str = Field(examples=["Что ты умеешь?"], description="Search prompt")
