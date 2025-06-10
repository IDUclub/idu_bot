import json
from pathlib import Path

from iduconfig import Config

from src.common.exceptions.http_exception import http_exception
from src.elastic.elastic_service import ElasticService
from src.idu_llm.idu_llm_service import IduLLMService
from src.llm.llm_service import LlmService
from src.vectorizer.vectorizer_service import VectorizerService


#ToDo Remove to cache
index_mapper = {
    'general': 'Общее',
    'investment': 'Инвестиционная',
    'pre_design': 'Предпроектная',
    'design': 'Проектная',
    'construction': 'Строительная',
    'operation': 'Эксплуатационная',
    'decommission': 'Ликвидационная'
}


config = Config()
model = VectorizerService(config)
llm_service = LlmService(config)
elastic_client = ElasticService(config, model, llm_service, index_mapper)
idu_llm_client = IduLLMService(llm_service, elastic_client, model)
