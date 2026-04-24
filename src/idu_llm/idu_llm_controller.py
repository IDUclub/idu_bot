import json
from typing import AsyncIterable, NoReturn

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketException, status
from fastapi.sse import EventSourceResponse, ServerSentEvent
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


@idu_llm_router.get("/stream/generate", response_class=EventSourceResponse)
async def generate_stream_response(
    message_info: BaseLlmRequest | ScenarioRequestDTO,
) -> AsyncIterable:
    """
    Min function to generate response through bot api.
    Args:
        message_info (BaseLlmRequest): Message to send.
    Returns:
        response (EventSourceResponse): Sse stream response.
    """

    async for chunk in idu_llm_client.generate_simple_stream_response(message_info):
        if isinstance(chunk, bool):
            yield {"type": "chunk", "content": {"text": "", "done": chunk}}
        else:
            if chunk["type"] == "status":
                yield {
                    "type": "status",
                    "content": {"status": "generation", "text": chunk["chunk"]},
                }
            else:
                yield {
                    "type": "chunk",
                    "content": {"text": chunk["chunk"], "done": False},
                }


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
                    if isinstance(text, dict):
                        await websocket.send_text(json.dumps(text))
                    if isinstance(text, str):
                        if text:
                            await websocket.send_text(
                                json.dumps({"type": "text", "chunk": text})
                            )
                    elif isinstance(text, list):
                        await websocket.send_text(
                            json.dumps({"type": "feature_collections", "chunk": text})
                        )
                else:
                    await websocket.close(1000, "Stream ended")
        else:
            async for text in idu_llm_client.generate_simple_stream_response(
                message_info
            ):
                if text != False:
                    if text["chunk"]:
                        await websocket.send_text(json.dumps(text))
                    else:
                        continue
                else:
                    await websocket.close(1000, "Stream ended")
    except HTTPException as http_e:
        logger.exception(http_e)
        if http_e.status_code == 400:
            json_to_send = {"http_code": http_e.status_code, **http_e.detail}
            await websocket.send_json(json_to_send)
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
    except Exception as e:
        logger.exception(e)
        await websocket.send_text(repr(e))
        await websocket.close(code=1011, reason=e.__str__())
