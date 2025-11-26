import json
from typing import AsyncIterator

import requests

from src.common.exceptions.http_exception import http_exception
from src.elastic.elastic_service import ElasticService
from src.llm.llm_service import LlmService
from src.vectorizer.vectorizer_service import VectorizerService

from .dto.base_request_dto import BaseLlmRequest
from .dto.scenario_request_dto import ScenarioRequestDTO


class IduLLMService:

    def __init__(
        self,
        llm_service: LlmService,
        elastic_client: ElasticService,
        vectorizer_model: VectorizerService,
    ):

        self.llm_service = llm_service
        self.elastic_client = elastic_client
        self.vectorizer_model = vectorizer_model

    async def generate_response(self, message_info: BaseLlmRequest) -> str:
        try:
            embedding = self.vectorizer_model.embed(message_info.user_request)
        except Exception as e:
            raise http_exception(
                500,
                "Error during creating embedding",
                _input=message_info.user_request,
                _detail=e.__str__(),
            )
        try:
            elastic_response = await self.elastic_client.search(
                embedding, message_info.index_name
            )
        except Exception as e:
            raise http_exception(
                500,
                "Error during creating extracting elastic document",
                _input={
                    "message_info.user_request": message_info.user_request,
                    "embedding": embedding,
                },
                _detail=e.__str__(),
            )
        context = ";".join(
            [
                resp["_source"]["body"].rstrip()
                for resp in elastic_response["hits"]["hits"]
            ]
        )
        headers, data = await self.llm_service.generate_request_data(
            message_info.user_request, context, False
        )
        try:
            llm_response = requests.post(
                f"{self.llm_service.url}/api/generate",
                headers=headers,
                data=json.dumps(data),
            )
        except Exception as e:
            raise http_exception(
                500,
                "Error during retrieving response",
                _input={
                    "message_info.user_request": message_info.user_request,
                    "embedding": embedding,
                    "context": context,
                    "llm_request_headers": headers,
                    "formed_data": data,
                },
                _detail=e.__str__(),
            )
        if llm_response.status_code != 200:
            raise http_exception(
                llm_response.status_code,
                "Error during generating llm request",
                _input={
                    "message_info.user_request": message_info.user_request,
                    "embedding": embedding,
                    "context": context,
                    "llm_request_headers": headers,
                    "formed_data": data,
                },
                _detail=llm_response.text,
            )
        return llm_response.json()

    async def generate_simple_stream_response(
        self, message_info: BaseLlmRequest
    ) -> AsyncIterator[str | bool]:
        try:
            embedding = self.vectorizer_model.embed(message_info.user_request)
            yield "Формирую контекст\n"
        except Exception as e:
            raise http_exception(
                500,
                "Error during creating embedding",
                _input=message_info.user_request,
                _detail=e.__str__(),
            )
        try:
            elastic_response = await self.elastic_client.search(
                embedding, message_info.index_name
            )
            yield "Анализирую информацию\n"
        except Exception as e:
            raise http_exception(
                500,
                "Error during creating extracting elastic document",
                _input={
                    "message_info.user_request": message_info.user_request,
                    "embedding": embedding,
                },
                _detail=e.__str__(),
            )
        context = ";".join(
            [
                resp["_source"]["body"].rstrip()
                for resp in elastic_response["hits"]["hits"]
            ]
        )
        headers, data = await self.llm_service.generate_request_data(
            message_info.user_request, context, True
        )
        with requests.post(
            f"{self.llm_service.url}/api/generate",
            headers=headers,
            data=json.dumps(data),
            stream=True,
        ) as response:
            if response.status_code == 200:
                for chunk in response.iter_content(chunk_size=512 * 1024):
                    chunk = json.loads(chunk)
                    if not chunk["done"]:
                        yield chunk["response"]
                    else:
                        yield False

    async def generate_scenario_stream_response(
        self, message_info: ScenarioRequestDTO
    ) -> AsyncIterator[str | bool | list]:
        index_name = f"{message_info.scenario_id}&{message_info.get_mode_index()}"
        try:
            embedding = self.vectorizer_model.embed(message_info.user_request)
            yield "Формирую контекст\n"
        except Exception as e:
            raise http_exception(
                500,
                "Error during creating embedding",
                _input=message_info.user_request,
                _detail=e.__str__(),
            )
        try:
            elastic_response = await self.elastic_client.search_scenario(
                embedding, index_name, message_info.object_id
            )
            yield "Анализирую информацию\n"
        except Exception as e:
            raise http_exception(
                500,
                "Error during creating extracting elastic document",
                _input={
                    "message_info.user_request": message_info.user_request,
                    "embedding": embedding,
                },
                _detail=e.__str__(),
            )
        context = ";".join(
            [resp["_source"]["body"].rstrip() for resp in elastic_response]
        )
        if message_info.get_mode_index() == "general":
            feature_collections = [
                resp["_source"]["feature_collection"] for resp in elastic_response
            ]
        elif message_info.get_mode_index() == "analyze" and message_info.object_id:
            feature_collections = None
        else:
            features = [
                {
                    "type": "Feature",
                    "geometry": resp["_source"]["location"],
                    "properties": resp["_source"]["properties"],
                }
                for resp in elastic_response
            ]
            feature_collections = [{"type": "FeatureCollection", "features": features}]
        yield feature_collections

        headers, data = await self.llm_service.generate_request_data(
            message_info.user_request, context, True
        )
        with requests.post(
            f"{self.llm_service.url}/api/generate",
            headers=headers,
            data=json.dumps(data),
            stream=True,
        ) as response:
            if response.status_code == 200:
                for chunk in response.iter_content(chunk_size=512 * 1024):
                    chunk = json.loads(chunk)
                    if not chunk["done"]:
                        yield chunk["response"]
                    else:
                        yield False
