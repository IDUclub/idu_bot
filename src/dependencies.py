import json
from pathlib import Path

from iduconfig import Config

from src.common.constants.index_mapper import index_mapper, reverse_index_mapper
from src.common.exceptions.http_exception import http_exception
from src.elastic.elastic_service import ElasticService
from src.idu_llm.idu_llm_service import IduLLMService
from src.llm.llm_service import LlmService
from src.vectorizer.vectorizer_service import VectorizerService

config = Config()
model = VectorizerService(config)
llm_service = LlmService(config)
elastic_client = ElasticService(
    config, model, llm_service, index_mapper, reverse_index_mapper
)
idu_llm_client = IduLLMService(llm_service, elastic_client, model)
