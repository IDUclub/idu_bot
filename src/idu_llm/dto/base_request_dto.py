from pydantic import BaseModel, Field, field_validator

from src.dependencies import http_exception
from src.common.constants.index_mapper import reverse_index_mapper


class BaseLlmRequest(BaseModel):

    index_name: str = Field(
        default="Общее",
        examples=["Общее"],
        description="ElasticSearch index name to use as context db",
    )
    user_request: str = Field(..., examples=["Что ты умеешь?"])

    @field_validator("index_name", mode="after")
    @classmethod
    def validate_index(cls, value: str) -> str:
        if name:=reverse_index_mapper.get(value):
            return name
        raise http_exception(
            400,
            "No matching elastic index found",
            _input=value,
            _detail={"available_indexes": list(reverse_index_mapper.keys())},
        )