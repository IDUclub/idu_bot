from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, UploadFile

from src.dependencies import config, elastic_client
from src.elastic.dto.create_scenario_index_dto import CreateScenarioIndexDTO
from src.elastic.dto.elastic_search_dto import ElasticSearchDTO
from src.elastic.dto.scenario_search_dto import ScenarioSearchDTO
from src.elastic.dto.upload_document_dto import UploadDocumentDTO
from src.elastic.dto.upload_scenario_dto import UploadScenarioDTO

elastic_router = APIRouter()
tag = ["LLM Controller"]
cfg_tag = ["Config Controller"]


@elastic_router.get("/llm/indexes", tags=tag)
async def get_available_indexes():
    return await elastic_client.get_available_indexes()


@elastic_router.post("/llm/indexes", tags=tag)
async def create_index(index_name: str, en: str):
    return await elastic_client.create_index(index_name, en)


@elastic_router.post("/llm/index/{scenario_id}", tags=tag)
async def create_scenario_index(
    scenario_id: int,
    dto: Annotated[CreateScenarioIndexDTO, Depends(CreateScenarioIndexDTO)],
):

    return await elastic_client.create_scenario_index(dto.get_index_name(scenario_id))


@elastic_router.get("/llm/all_indexes_eng", tags=tag)
async def get_all_indexes():

    return await elastic_client.get_all_indexes()


@elastic_router.get("/llm/scenario/indexes/{scenario_id}", tags=tag)
async def get_scenario_indexes(scenario_id: int):

    return await elastic_client.get_available_scenario_indexes(scenario_id)


@elastic_router.get("/llm/scenario/modes", tags=tag)
async def get_scenario_modes() -> list[str]:

    return ["Анализ объекта", "Анализ территории проекта", "Анализ по объектам проекта"]


@elastic_router.put("llm/index_map", tags=tag)
async def update_index_map(map: dict[str, str]):
    return await elastic_client.update_index_mapping(map)


@elastic_router.post("/llm/scenario/upload_data", tags=tag)
async def upload_data_to_scenario_index(
    dto: Annotated[UploadScenarioDTO, Depends(UploadScenarioDTO)],
):

    if dto.mode == "Анализ территории проекта":
        return await elastic_client.upload_common_scenario(
            f"{dto.scenario_id}&{dto.get_mode_index()}", dto.data
        )
    else:
        return await elastic_client.upload_analyze_scenario(
            f"{dto.scenario_id}&{dto.get_mode_index()}", dto.data
        )


@elastic_router.post("/llm/upload_document", tags=tag)
async def upload_document(
    file: UploadFile, dto: Annotated[UploadDocumentDTO, Depends(UploadDocumentDTO)]
):
    return await elastic_client.upload_to_index(
        await file.read(),
        dto.doc_name,
        dto.index_name,
        dto.table_context_size,
        dto.text_questions_num,
        dto.table_questions_num,
    )


@elastic_router.delete("/llm/delete_documents/{index_name}", tags=tag)
async def delete_document(index_name: str):
    return await elastic_client.delete_documents_from_index(index_name)


@elastic_router.delete("/llm/delete_index/{index_name}", tags=tag)
async def delete_documents(index_name: str):
    return await elastic_client.delete_index(index_name)


@elastic_router.get("/llm/search", tags=tag)
async def search(dto: Annotated[ElasticSearchDTO, Depends(ElasticSearchDTO)]):
    return await elastic_client.search(elastic_client.encode(dto.prompt))


@elastic_router.get("/llm/search/scenario/{scenario_id}")
async def search_scenario(
    scenario_id: int, dto: Annotated[ScenarioSearchDTO, Depends(ScenarioSearchDTO)]
):

    return await elastic_client.search_scenario(
        elastic_client.encode(dto.prompt),
        dto.get_index_name(scenario_id),
        dto.object_id,
    )


@elastic_router.put("/cfg/configure", tags=cfg_tag)
async def configure(
    body: Annotated[dict, Body()],
):
    for k, v in body.items():
        config.set(k, v)


@elastic_router.get("/cfg", tags=cfg_tag)
async def get_env(key: Annotated[str, Query()]):
    return config.get(key)
