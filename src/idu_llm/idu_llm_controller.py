import json
from typing import NoReturn

from fastapi import APIRouter, WebSocket
from loguru import logger

from src.dependencies import idu_llm_client

from .dto.base_request_dto import BaseLlmRequest
from .dto.scenario_request_dto import ScenarioRequestDTO
from .dto.validate_in_order import validate_in_order

idu_llm_router = APIRouter()


@idu_llm_router.post("/generate")
async def generate(
    message_info: BaseLlmRequest | ScenarioRequestDTO,
):
    """
    Main function to generate response through bot api

    Args:

        message_info (BaseLlmRequest): Message to send

    Returns:

        response (dict): Generated response
    """

    if message_info.isinstance(BaseLlmRequest):
        response = await idu_llm_client.generate_response(message_info)
    return response


@idu_llm_router.websocket("/ws/generate")
async def websocket_llm_endpoint(websocket: WebSocket) -> NoReturn:
    """
    WebSocket endpoint to generate response through bot api

    Args:

        websocket (WebSocket): WebSocket connection

    Returns:

        None
    """

    await websocket.accept()
    try:
        request = await websocket.receive_json()
        message_info = validate_in_order(request)
        if message_info.index_name == "project":
            async for text in idu_llm_client.generate_scenario_stream_response(
                message_info
            ):
                if text != False:
                    if isinstance(text, str):
                        await websocket.send_text(
                            json.dumps({"type": "text", "chunk": text})
                        )
                    elif isinstance(text, list):
                        await websocket.send_json(
                            json.dumps({"type": "feature_collections", "chunk": text})
                        )
                else:
                    await websocket.close(1000, "Stream ended")
        else:
            async for text in idu_llm_client.generate_simple_stream_response(
                message_info
            ):
                if text != False:
                    await websocket.send_text(text)
                else:
                    await websocket.close(1000, "Stream ended")
    except Exception as e:
        logger.exception(e)
        await websocket.send_text(repr(e))
        await websocket.close(code=1011, reason=e.__str__())
