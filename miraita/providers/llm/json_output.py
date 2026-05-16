import json
from dataclasses import is_dataclass
from typing import Any, Generic, Literal, TypeVar, cast

import litellm
from arclet.entari.config.action import config_model_validate

TOutput = TypeVar("TOutput")
OutputType = Literal["json_object"] | type[Any] | dict[str, Any]


class StructuredModelResponse(litellm.ModelResponse, Generic[TOutput]):
    output: TOutput | Any | None = None

    @classmethod
    def from_model_response(
        cls,
        response: litellm.ModelResponse,
        output: TOutput | Any | None,
    ) -> "StructuredModelResponse[TOutput]":
        payload = response.model_dump()
        instance = cls(**payload)
        instance.output = output
        return instance


def parse_output(content: str | None, output: OutputType) -> Any:
    if content is None:
        raise RuntimeError("model output is empty")

    data = json.loads(content)

    if output == "json_object" or isinstance(output, dict):
        return data

    elif isinstance(output, type):
        return validate_output(data, output)

    return data


def validate_output(data: Any, schema_type: type[TOutput]) -> TOutput:
    if not isinstance(data, dict):
        return cast(TOutput, data)

    try:
        return cast(TOutput, config_model_validate(schema_type, data))
    except Exception:
        pass

    if is_dataclass(schema_type):
        return cast(TOutput, schema_type(**data))

    return cast(TOutput, data)
