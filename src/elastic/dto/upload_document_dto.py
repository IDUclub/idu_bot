from pydantic import BaseModel, Field


class UploadDocumentDTO(BaseModel):
    index_name: str = Field(description="index name in elastic")
