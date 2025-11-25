from pydantic import ValidationError

from .base_request_dto import BaseLlmRequest
from .scenario_request_dto import ScenarioRequestDTO


def validate_in_order(message_info: dict):

    errors = []
    try:
        return BaseLlmRequest(**message_info)
    except Exception as e:
        errors.append(e)
    try:
        return ScenarioRequestDTO(**message_info)
    except Exception as e:
        errors.append(e)

    raise ValidationError(errors)
