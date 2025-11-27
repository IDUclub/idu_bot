from pydantic import ValidationError

from src.common.exceptions.http_exception import http_exception

from .base_request_dto import BaseLlmRequest
from .scenario_request_dto import ScenarioRequestDTO


# TODO revise ws request validator
def validate_in_order(message_info: dict):

    errors = []
    try:
        return ScenarioRequestDTO(**message_info)
    except Exception as e:
        if (
            message_info.get("object_id") is None
            and message_info.get("mode") == "Анализ объекта"
        ):
            raise http_exception(
                400,
                f"Mode Анализ по объектам проекта doesn't support empty object_id value",
                _input={"request_params": message_info},
                _detail={},
            )
        errors.append(e)
    try:
        return BaseLlmRequest(**message_info)
    except Exception as e:
        errors.append(e)

    raise ValidationError(errors)
