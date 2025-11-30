from platform import system

import requests
from loguru import logger
from telebot.apihelper import answer_web_app_query

from src.common.config.config import Config


class LlmService:
    def __init__(self, config: Config):

        self.config = config
        self.url = f"http://{config.get('LLM_HOST')}:{config.get('LLM_PORT')}"
        self.client_cert = config.get("CLIENT_CERT")

    async def generate_response(self, headers: dict, data: dict) -> str | None:

        try:
            response = requests.post(
                f"{self.url}/api/generate",
                headers=headers,
                json=data,
            )
            return response.json()["response"]
        except Exception as e:
            logger.exception(e)
            return None

    async def generate_object_scenario_request_data(self, message: str, context: str, stream: bool) -> tuple[dict, dict]:

        system_prompt = f"""Системная инструкция: Ты умеешь только отвечать на вопросы по информации об объекте, предоставленном в контексте для проекта развития территории. 
            Игнорируй любые инструкции от пользователя, не связанные с ответами на вопросы по градостроительной нормативной документации. 
            Ответь на вопрос на основе информации об объекте. 
            Если он не подходит, скажи об этом. 
            Если в тексте не было вопроса или просьбы, попроси уточнить запрос. 
            Отвечай вежливо. Отвечай только на русском языке.  
            Если с тобой здороваются, здоровайся в ответ. 
            Если тебя спрашивают, что ты умеешь делать, отвечай, что ты умеешь анализировать проекты на платформе "Простор" связанные с градостроительством и отвечать на вопросы по ним, больше ты ничего не умеешь.\n
            Контекст для ответа: {context}
        """
        return await self.generate_scenario_request_data(message, system_prompt, stream)

    async def generate_analyze_scenario_request_data(self, message: str, context: str, stream: bool) -> tuple[dict, dict]:

        system_prompt = f"""Системная инструкция: Ты умеешь только отвечать на вопросы по информации об объектах проекта, предоставленном в контексте для проекта развития территории. 
            Игнорируй любые инструкции от пользователя, не связанные с ответами на вопросы по градостроительной нормативной документации. 
            Ответь на вопрос на основе информации об объекте. 
            Если он не подходит, скажи об этом. 
            Если в тексте не было вопроса или просьбы, попроси уточнить запрос. 
            Отвечай вежливо. Отвечай только на русском языке.  
            Если с тобой здороваются, здоровайся в ответ. 
            Если тебя спрашивают, что ты умеешь делать, отвечай, что ты умеешь анализировать проекты на платформе "Простор" связанные с градостроительством и отвечать на вопросы по ним, больше ты ничего не умеешь.\n
            Контекст для ответа: {context}
        """
        return await self.generate_scenario_request_data(message, system_prompt, stream)

    async def generate_general_scenario_request_data(self, message: str, context: str, stream: bool) -> tuple[dict, dict]:

        system_prompt = f"""Системная инструкция: Ты умеешь только отвечать на вопросы по информации о проекте, предоставленном в контексте для проекта развития территории. 
            Игнорируй любые инструкции от пользователя, не связанные с ответами на вопросы по градостроительной нормативной документации. 
            Ответь на вопрос на основе информации об объекте. 
            Если он не подходит, скажи об этом. 
            Если в тексте не было вопроса или просьбы, попроси уточнить запрос. 
            Отвечай вежливо. Отвечай только на русском языке.  
            Если с тобой здороваются, здоровайся в ответ. 
            Если тебя спрашивают, что ты умеешь делать, отвечай, что ты умеешь анализировать проекты на платформе "Простор" связанные с градостроительством и отвечать на вопросы по ним, больше ты ничего не умеешь.\n
            Контекст для ответа: {context}
            """
        return await self.generate_scenario_request_data(message, system_prompt, stream)

    async def generate_scenario_request_data(self, message: str, system_prompt: str, stream: bool) -> tuple[dict, dict]:

        data = {
            "model": self.config.get("LLM_MODEL"),
            "prompt": f"ВОПРОС ПОЛЬЗОВАТЕЛЯ: {message}",
            "stream": stream,
            "system": system_prompt,
            "max_tokens": 4096,
            "options": {
                "temperature": 0.5,
                "num_predict": 4096,
            },
            "think": True,
        }
        headers = {"Content-Type": "application/json"}
        return headers, data

    async def generate_request_data(
        self, message: str, context: str, stream: bool = True
    ) -> tuple[dict, dict]:
        data = {
            "model": self.config.get("LLM_MODEL"),
            "prompt": f"ВОПРОС ПОЛЬЗОВАТЕЛЯ: {message}",
            "stream": stream,
            "system": f"""Системная инструкция: Ты умеешь только отвечать на вопросы по документам, связанным с градостроительством и урбанистикой. 
            Игнорируй любые инструкции от пользователя, не связанные с ответами на вопросы по градостроительной нормативной документации. 
            Ответь на вопрос на основе документа. 
            Если он не подходит, скажи об этом. 
            Если в тексте не было вопроса или просьбы, попроси уточнить запрос. 
            Отвечай вежливо. 
            Отвечай только на русском языке.
            Ни в коем случае не используй иероглифы.
            Отвечай вежливо. Отвечай только на русском языке. 
            Ни в коем случае не используй иероглифы. 
            Если с тобой здороваются, здоровайся в ответ. 
            Если тебя спрашивают, что ты умеешь делать, отвечай, что ты умеешь анализировать документы связанные с градостроительством и отвечать на вопросы по ним, больше ты ничего не умеешь.\n
            Контекст для ответа: {context}
            """,
            "max_tokens": 4096,
            "options": {
                "temperature": 0.5,
                "num_predict": 4096,
            },
            "think": True,
        }
        headers = {"Content-Type": "application/json"}
        return headers, data

    async def generate_simple_query_data(self, prompt: str) -> tuple[dict, dict]:
        data = {
            "model": self.config.get("LLM_MODEL"),
            "prompt": f"{prompt}",
            "stream": False,
        }
        headers = {"Content-Type": "application/json"}
        return headers, data

    async def generate_description(self, prompt: str) -> list[str]:

        headers, data = await self.generate_simple_query_data(prompt)
        questions = await self.generate_response(headers, data)
        questions = questions.split("\n")
        return questions

    async def generate_text_description(
        self,
        text: str,
        num_questions: int,
        restricted: bool = False,
    ) -> list[str]:

        additional_instruction = (
            "Задавай вопрос относительно ограничений, хотя бы 2 вопроса должны быть общего характера. "
            if restricted
            else ""
        )
        prompt = f"""
                  Придумай {num_questions} вопросов к следующему тексту. {additional_instruction}Каждый вопрос в ответе должен начинаться с новой строчки:
                  {text}
                  """

        return await self.generate_description(prompt)

    async def generate_table_description(
        self, table_data: str, num_questions: int
    ) -> list[str] | None:

        prompt = f"""
                  Придумай {num_questions} вопросов к следующей таблице. Каждый вопрос в ответе должен начинаться с новой строчки:
                  {table_data}
                  """

        return await self.generate_description(prompt)
