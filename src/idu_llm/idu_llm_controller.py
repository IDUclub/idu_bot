from .dto.base_request_dto import BaseLlmRequest

from fastapi import APIRouter

from src.dependencies import idu_llm_client


idu_llm_router = APIRouter()


@idu_llm_router.post("/generate")
async def generate(
    message_info: BaseLlmRequest,
):
    """
    Main function to generate response through bot api

    Args:

        message (str): Message to send

    Returns:

        response (dict): Generated response
    """

    response = await idu_llm_client.generate_response(message_info)
    return response
