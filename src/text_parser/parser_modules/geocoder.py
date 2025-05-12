import json

from loguru import logger
import requests
import nltk

from src.dependencies import llm_service, http_exception
from src.llm.llm_service import LlmService


nltk.download('stopwords')
nltk.download('punkt')
nltk.download('punkt_tab')


class Geocoder:

    def __init__(self, llm_service: LlmService):

        self.llm_service = llm_service

    async def extract_ner(self, text: str) -> list[str] | None:

        req_data = await llm_service.generate_simple_query_data(text)
        url = f"{self.llm_service.url}/api/generate"
        try:
            with requests.post(
                    url,
                    **req_data
            ) as response:
                if response.status_code == 200:
                    res = response.json()["response"].split(", ")
                    if res:
                        return res
                    return None
                else:
                    logger.error(f"Error during llm request: {response.text}")
                    raise http_exception(
                        response.status_code,
                        msg=f"Error during llm request: {response.text}",
                        _input=req_data,
                        _detail={"error": response.text}
                    )
        except Exception as e:
            logger.error(e)
            return None
