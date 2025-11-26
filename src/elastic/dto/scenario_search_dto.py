from typing import Literal

from pydantic import Field

from .elastic_search_dto import ElasticSearchDTO


class ScenarioSearchDTO(ElasticSearchDTO):

    mode: Literal[
        "Анализ объекта", "Анализ территории проекта", "Анализ по объектам проекта"
    ] = Field(
        examples=["Анализ территории проекта"], description="Scenario analyses mode"
    )
    object_id: int | None = Field(
        default=None,
        examples=[1474596],
        description="Object ID from Scenario to retrieve data on",
    )

    def get_mode_index(self) -> str:

        match self.mode:
            case "Анализ oбъекта":
                return "analyze"
            case "Анализ по объектам проекта":
                return "analyze"
            case "Анализ территории проекта":
                return "general"
            case _:
                raise Exception("Pydantic validation failed")

    def get_index_name(self, scenario_id: int) -> str:

        return f"{scenario_id}&{self.get_mode_index()}"
