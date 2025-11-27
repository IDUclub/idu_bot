import io

from docx import Document
from elastic_transport import ObjectApiResponse
from elasticsearch import Elasticsearch
from elasticsearch.helpers import BulkIndexError, bulk
from fastapi import HTTPException
from loguru import logger
from tqdm import tqdm

from src.common.config.config import Config
from src.dependencies import http_exception
from src.llm.llm_service import LlmService
from src.vectorizer.vectorizer_service import VectorizerService

from .doc_parser import doc_parser


class ElasticService:
    def __init__(
        self,
        config: Config,
        vectorizer_service: VectorizerService,
        llm_service: LlmService,
        index_mapper: dict[str, str],
        reverse_index_mapper: dict[str, str],
    ):
        self.client = Elasticsearch(
            hosts=[f"http://{config.get('ELASTIC_HOST')}:{config.get('ELASTIC_PORT')}"]
        )
        self.config = config
        self.vectorizer_service = vectorizer_service
        self.llm_service = llm_service
        self.index_mapper = index_mapper
        self.reverse_index_mapper = reverse_index_mapper

    async def check_indexes(self):
        for index in self.index_mapper.keys():
            if not self.client.indices.exists(index=index):
                await self.create_index(self.index_mapper[index], index)

    async def get_all_indexes(self) -> list[str]:

        all_indices = self.client.indices.get_alias(index="*")
        return [
            index
            for index in all_indices
            if not index.startswith(".") and not index.startswith("_")
        ]

    async def get_available_indexes(self) -> list[str]:

        index_list = await self.get_all_indexes()

        indexes_ru_name = [
            self.index_mapper.get(index)
            for index in index_list
            if self.index_mapper.get(index)
        ]
        return indexes_ru_name

    async def get_available_scenario_indexes(self, scenario_id: int) -> list[str]:

        index_list = await self.get_all_indexes()
        return [i for i in index_list if str(scenario_id) in i]

    async def update_index_mapping(
        self,
        index_map: dict[str, str],
    ) -> str:

        # ToDo Add mapping
        try:
            self.index_mapper.update(index_map)
            # with open ("./cache/index_mapper.json", "w") as index_mapper_file:
            #     json.dump(index_map, index_mapper_file)
            return "Index mapper updated."
        except Exception as e:
            logger.error(e)
            raise http_exception(
                500,
                "Error updating index mapper.",
                _input=index_map,
                _detail={
                    "error": e.__str__(),
                },
            )

    async def create_index(self, index_name: str, en: str):

        if self.client.indices.exists(index=en):
            raise http_exception(
                400,
                "Index already exists.",
                _input={"index": en},
                _detail={"existing)_indexes": list(self.index_mapper.keys())},
            )

        try:
            resp = self.client.indices.create(
                index=en,
                body={
                    "mappings": {
                        "properties": {
                            "body_vector": {
                                "type": "dense_vector",
                                "dims": 4096,
                                "index": True,
                                "similarity": "cosine",
                            },
                            "body": {"type": "text"},
                            "num_id": {"type": "long"},
                            "doc_name": {
                                "type": "text",
                                "fields": {
                                    "keywords": {
                                        "type": "keyword",
                                    }
                                },
                            },
                        }
                    }
                },
            )

            self.index_mapper[en] = index_name

            return resp.raw

        except Exception as e:
            raise http_exception(
                500,
                "Failed to create index",
                _input={"index_name": index_name},
                _detail={"error": e.__str__()},
            )

    async def create_scenario_index(self, index_name: str):

        if self.client.indices.exists(index=index_name):
            raise http_exception(
                400,
                "Index already exists.",
                _input={"index": index_name},
                _detail={"existing)_indexes": list(self.index_mapper.keys())},
            )
        body = {
            "mappings": {
                "properties": {
                    "body_vector": {
                        "type": "dense_vector",
                        "dims": 4096,
                        "index": True,
                        "similarity": "cosine",
                    },
                    "body": {"type": "text"},
                    "num_id": {"type": "long"},
                }
            }
        }
        if "general" in index_name:
            body["mappings"]["properties"].update(
                **{"feature_collection": {"type": "object", "enabled": True}}
            )
        else:
            body["mappings"]["properties"].update(
                **{
                    "location": {"type": "geo_shape"},
                    "properties": {"type": "object", "enabled": True},
                }
            )

        try:

            resp = self.client.indices.create(
                index=index_name,
                body=body,
            )

            return resp.raw

        except Exception as e:
            raise http_exception(
                500,
                "Failed to create index",
                _input={"index_name": index_name},
                _detail={"error": repr(e)},
            )

    async def delete_index(self, index_name: str):

        resp = self.client.options(ignore_status=[400, 404]).indices.delete(
            index=index_name
        )
        return resp.raw

    async def delete_documents_from_index(self, index_name: str) -> str:
        try:
            self.client.delete_by_query(
                index=index_name, body={"query": {"match_all": {}}}
            )
            return f"Successfully deleted all documents from index {index_name}"
        except Exception as e:
            logger.exception(e)
            raise HTTPException(status_code=500, detail=e.__str__())

    async def search(
        self, embedding: list, index_name: str | None = None
    ) -> ObjectApiResponse:

        if index_name is None:
            index_name = self.config.get("ELASTIC_DOCUMENT_INDEX")

        query_body = {
            "knn": {
                "field": "body_vector",
                "query_vector": embedding,
                "k": int(self.config.get("ELASTIC_K")),
                "num_candidates": int(self.config.get("NUM_CANDIDATES")),
            },
            "_source": ["body"],
            "min_score": float(self.config.get("MIN_SCORE")),
        }
        return self.client.search(index=index_name, body=query_body)

    async def search_scenario(
        self, embedding: list, index_name: str, object_id_value: int | None
    ) -> list[str]:

        query_body = {
            "knn": {
                "field": "body_vector",
                "query_vector": embedding,
                "k": int(self.config.get("ELASTIC_K")),
                "num_candidates": 30,
            },
        }

        if object_id_value is not None:
            query_body["query"] = {
                "bool": {"filter": [{"term": {"object_id": object_id_value}}]}
            }

        response = self.client.search(index=index_name, body=query_body)
        response_list = []
        for i in response["hits"]["hits"]:
            if i not in response_list:
                response_list.append(i)
        return response_list

    @staticmethod
    async def create_analyze_scenario_row_to_upload(
        text: str,
        doc_id: int,
        object_id: int,
        vector: list,
        location: dict,
        properties: dict,
    ):

        return {
            "_id": str(doc_id),
            "num_id": doc_id,
            "text": text,
            "doc_id": doc_id,
            "object_id": object_id,
            "vector": vector,
            "location": location,
            "properties": properties,
        }

    @staticmethod
    async def create_general_scenario_row_to_upload(
        text: str,
        doc_id: int,
        vector: list,
        feature_collection: dict,
    ):

        return {
            "_id": str(doc_id),
            "num_id": doc_id,
            "body": text,
            "body_vector": vector,
            "feature_collection": feature_collection,
        }

    async def upload_analyze_scenario(
        self, index_name: str, data_to_upload: list, num_questions: int = 5
    ):

        num_ids = 0
        docs_to_upload = []
        for row in tqdm(
            data_to_upload, desc=f"Forming docs to elastic index {index_name}"
        ):
            text_questions = await self.llm_service.generate_text_description(
                row["text"], num_questions
            )
            for question in text_questions:
                num_ids += 1
                vector = self.encode(question)
                current_doc = await self.create_analyze_scenario_row_to_upload(
                    row["text"],
                    num_ids,
                    row["object_id"],
                    vector,
                    row["location"],
                    row["properties"],
                )
                docs_to_upload.append(current_doc)

        if docs_to_upload:
            try:
                bulk(
                    self.client, docs_to_upload, index=index_name, request_timeout=1200
                )
            except BulkIndexError as e:
                for error in e.errors:
                    print(error)
                    raise
        return index_name

    async def upload_common_scenario(
        self, index_name: str, data_to_upload: list, num_questions: int = 20
    ):

        num_ids = 0
        docs_to_upload = []
        for row in tqdm(
            data_to_upload, desc=f"Forming docs to elastic index {index_name}"
        ):
            text_questions = await self.llm_service.generate_text_description(
                row["text"], num_questions, True if row["feature_collection"] else False
            )
            for question in text_questions:
                num_ids += 1
                vector = self.encode(question)
                current_doc = await self.create_general_scenario_row_to_upload(
                    row["text"],
                    num_ids,
                    vector,
                    row["feature_collection"],
                )
                docs_to_upload.append(current_doc)

        if docs_to_upload:

            try:
                bulk(
                    self.client, docs_to_upload, index=index_name, request_timeout=1200
                )
            except BulkIndexError as e:
                for error in e.errors:
                    print(error)
                return

        return index_name

    async def get_last_index(self, index_name: str) -> int:
        query_body = {"size": 1, "sort": [{"num_id": {"order": "desc"}}]}
        try:
            last_id_data = self.client.search(index=index_name, body=query_body)
        except Exception as e:
            logger.exception(e)
            raise HTTPException(status_code=500, detail=e.__str__())
        if last_id_data.body["hits"]["hits"]:
            return last_id_data.body["hits"]["hits"][0]["_source"]["num_id"]
        return 0

    async def create_doc_to_upload(
        self,
        text: str,
        doc_id: int,
        doc_name: str,
    ) -> dict[str, str | list]:

        vector = self.encode(text)
        return {
            "_id": str(doc_id),
            "num_id": doc_id,
            "body": text,
            "body_vector": vector,
            "doc_name": doc_name,
        }

    async def create_paragraph_to_upload(
        self, text: str, num_questions: int, last_doc_id: int, doc_name: str
    ) -> tuple[list[dict[str, str | int]], int]:

        docs_to_add = []
        text_questions = await self.llm_service.generate_text_description(
            text, num_questions
        )
        for i in range(1, len(text_questions) + 2):
            if i > len(text_questions):
                docs_to_add.append(
                    {
                        "_id": str(last_doc_id + i),
                        "num_id": last_doc_id + i,
                        "body": text,
                        "body_vector": self.encode(text),
                        "doc_name": doc_name,
                    }
                )
            else:
                docs_to_add.append(
                    {
                        "_id": str(last_doc_id + i),
                        "num_id": last_doc_id + i,
                        "body": text,
                        "body_vector": self.encode(text_questions[i - 1]),
                        "doc_name": doc_name,
                    }
                )
            return docs_to_add, last_doc_id + len(text_questions) + 1

    async def create_table_to_upload(
        self,
        table_with_context: tuple[str, str, str],
        num_questions: int,
        last_doc_id: int,
        doc_name: str,
    ) -> tuple[list[dict[str, str | int]], int]:

        docs_to_add = []
        table_questions = await self.llm_service.generate_table_description(
            table_with_context[1], num_questions
        )
        text = "\n".join(table_with_context)
        for i in range(1, len(table_questions) + 2):
            if i > len(table_questions):
                docs_to_add.append(
                    {
                        "_id": str(last_doc_id + i),
                        "num_id": last_doc_id + i,
                        "body": text,
                        "body_vector": self.encode(table_questions[i - 1]),
                        "doc_name": doc_name,
                    }
                )
            else:
                docs_to_add.append(
                    {
                        "_id": str(last_doc_id + i),
                        "num_id": last_doc_id + i,
                        "body": text,
                        "body_vector": self.encode(table_questions[i - 1]),
                        "doc_name": doc_name,
                    }
                )

        return docs_to_add, last_doc_id + len(table_questions) + 1

    async def upload_to_index(
        self,
        file: bytes,
        doc_name: str,
        index_name: str,
        table_context_size: int,
        text_questions_num: int,
        table_questions_num: int,
    ):
        if not self.client.indices.exists(index=index_name):
            await self.create_index(index_name, self.index_mapper[index_name])
        documents = []
        full_doc = Document(io.BytesIO(file))
        last_id = await self.get_last_index(index_name)
        logger.info(
            f"Started uploading documents to index {index_name} from id {last_id}"
        )
        dock_blocks = [i for i in doc_parser.iter_contexts_for_vectorization(full_doc)]
        for index, entity in tqdm(
            enumerate(dock_blocks), total=len(dock_blocks), desc="Processing texts"
        ):
            if entity[1] == "text":
                text = entity[0]
                docs, last_id = await self.create_paragraph_to_upload(
                    text, text_questions_num, last_id, doc_name
                )
                documents += docs
            elif entity[1] == "table":
                table_data = entity[0]
                try:
                    table_with_context = (
                        "\n".join(
                            [
                                i[0]
                                for i in dock_blocks[
                                    max(index - table_context_size, 0) : index
                                ]
                                if i[1] == "text"
                            ]
                        ),
                        table_data,
                        "\n".join(
                            [
                                i[0]
                                for i in dock_blocks[index : index + table_context_size]
                                if i[1] == "text"
                            ]
                        ),
                    )
                except Exception as e:
                    logger.exception(e)
                    raise HTTPException(status_code=500, detail=e.__str__())
                docs, last_id = await self.create_table_to_upload(
                    table_with_context, table_questions_num, last_id, doc_name
                )
                documents += docs

        if documents:
            bulk(self.client, documents, index=index_name, request_timeout=1200)
        return index_name

    def encode(self, document: str) -> list:
        try:
            return self.vectorizer_service.embed(document)
        except Exception as e:
            raise HTTPException(500, str(e))
