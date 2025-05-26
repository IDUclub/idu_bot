from pydantic import BaseModel, Field


class BaseLlmRequest(BaseModel):

    user_request: str = Field(..., examples=["Что ты умеешь?"])
