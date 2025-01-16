import io

from elastic_transport import ObjectApiResponse
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from fastapi import HTTPException

from src.common.config.config import Config
from src.vectorizer.vectorizer_service import VectorizerService


class ElasticService:
    def __init__(self, config: Config, vectorizer_service: VectorizerService):
        self.client = Elasticsearch(hosts=[f"http://{config.get('ELASTIC_HOST')}:{config.get('ELASTIC_PORT')}"])
        self.config = config
        self.vectorizer_service = vectorizer_service

    async def search(self, embedding: list) -> ObjectApiResponse:
        index_name = self.config.get("ELASTIC_DOCUMENT_INDEX")
        query_body = {
            "knn": {
                "field": "body_vector",
                "query_vector": embedding,
                "k": 20,
                "num_candidates": 20
            },
            "_source": ["body"],
        }
        return self.client.search(index=index_name, body=query_body)

    async def upload_to_index(self, file: bytes, index_name: str):
        documents = []
        byte_file = io.BytesIO(file)
        # Open the file containing text.
        with io.TextIOWrapper(byte_file, encoding="utf-8") as documents_file:
            # Open the file in which the vectors will be saved.
            processed = 0
            # Processing 100 documents at a time.
            lines = documents_file.readlines()
            for i in range(len(lines)):
                if lines[i].rstrip() == "":
                    continue
                processed += 1
                # Create sentence embedding
                vector = self.encode(lines[i])
                doc = {
                    "_id": str(i),
                    "body": lines[i],
                    "body_vector": vector,
                }
                # Append JSON document to a list.
                documents.append(doc)
        try:
            self.client.indices.delete(index=index_name)
        except Exception as e:
            print(e)
        self.client.indices.create(index=index_name, body={
            "mappings": {
                "properties": {
                    "body_vector": {
                        "type": "dense_vector",
                        "dims": 1024,
                        "index": True,
                        "similarity": "cosine"
                    },
                    "body": {
                        "type": "text"
                    },
                }
            }})
        if documents:
            bulk(self.client, documents, index=index_name)
        print("Finished")
        return index_name

    def encode(self, document: str) -> list:
        try:
            return self.vectorizer_service.embed(document)
        except Exception as e:
            raise HTTPException(500, str(e))
