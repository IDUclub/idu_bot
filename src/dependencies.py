from pathlib import Path

from iduconfig import Config

from src.common.constants.index_mapper import index_mapper, reverse_index_mapper
from src.common.exceptions.http_exception import http_exception
from src.common.logging.init_logs import init_logs
from src.elastic.elastic_service import ElasticService
from src.idu_llm.idu_llm_service import IduLLMService
from src.llm.llm_service import LlmService
from src.logs.logs_service import LogsService
from src.vectorizer.vectorizer_service import VectorizerService

# TODO remove to dependencies injection
config = Config()
log_path = Path().resolve().absolute() / ".log"
init_logs(log_path)
logs_service = LogsService(log_path)
model = VectorizerService(config)
llm_service = LlmService(config)
elastic_client = ElasticService(
    config, model, llm_service, index_mapper, reverse_index_mapper
)
idu_llm_client = IduLLMService(llm_service, elastic_client, model)
