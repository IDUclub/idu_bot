from typing import Literal

from pydantic import BaseModel, Field


class UploadScenarioDTO(BaseModel):

    scenario_id: int = Field(
        examples=[1830], description="Project scenario id from Urban API"
    )
    mode: Literal[
        "Анализ объекта", "Анализ территории проекта", "Анализ по объектам проекта"
    ] = Field(examples=["Анализ территории проекта"], description="Index mode type")
    data: list[dict] = Field(description="Data to load to index from Urban API")

    def get_mode_index(self) -> str:

        match self.mode:
            case "Анализ oбъекта":
                return "analyze"
            case "Анали по объектам проекта":
                return "analyze"
            case "Анализ территории проекта":
                return "general"
            case _:
                raise Exception("Pydantic validation failed")
