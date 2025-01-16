from src.common.config.config import Config
from src.elastic.elastic_service import ElasticService
from src.llm.llm_service import LlmService
from src.vectorizer.vectorizer_service import VectorizerService

config = Config()
model = VectorizerService(config)
elastic_client = ElasticService(config, model)
llm_service = LlmService(config)
