from typing import Literal

from pydantic import Field, model_validator

from src.common.exceptions.http_exception import http_exception

from .base_request_dto import BaseLlmRequest


class ScenarioRequestDTO(BaseLlmRequest):

    scenario_id: int = Field(
        examples=["1830"], description="Scenario ID from Urban API"
    )
    mode: Literal[
        "Анализ объекта", "Анализ территории проекта", "Анализ по объектам проекта"
    ] = Field(
        examples=["Анализ территории проекта"], description="Scenario analyses mode"
    )
    object_id: int | None = Field(
        default=None,
        examples=["1474596"],
        description="Object ID from Urban API to retrieve data on",
    )

    @model_validator(mode="after")
    def validate_fields(self):

        if self.index_name != "project":
            raise http_exception(
                400,
                "Request to scenario index can have only 'Информация проекта' index name",
                _input=self.index_name,
                _detail={"request_params": self.model_dump_json()},
            )
        if self.mode == "Анализ объекта" and not self.object_id:
            raise http_exception(
                400,
                "Mode 'Анализ объекта' should contain object_id field to generate responses on",
                _input={"mode": self.mode, "object_id": self.object_id},
                _detail={"request_params": self.model_dump_json()},
            )

    def get_mode_index(self) -> str:

        match self.mode:
            case "Анализ объекта":
                return "analyze"
            case "Анализ по объектам проекта":
                return "analyze"
            case "Анализ территории проекта":
                return "general"
            case _:
                raise Exception("Pydantic validation failed")
