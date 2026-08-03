from __future__ import annotations

import json
from collections.abc import AsyncIterator, Callable
from dataclasses import is_dataclass
from typing import Any, Generic, Literal, TypeVar, cast

from agno.run.agent import RunOutput
from pydantic import BaseModel, TypeAdapter, ValidationError

TOutput = TypeVar("TOutput")
_OUTPUT_UNSET = object()


def prepare_output_schema(
    output: Literal["json_object"] | type[Any] | dict[str, Any] | None,
) -> tuple[type[BaseModel] | dict[str, Any] | None, TypeAdapter[Any] | None]:
    if output is None:
        return None, None
    if output == "json_object":
        return {"type": "object"}, None
    if isinstance(output, dict):
        return output, None
    if isinstance(output, type) and issubclass(output, BaseModel):
        return output, TypeAdapter(output)
    if isinstance(output, type) and is_dataclass(output):
        adapter = TypeAdapter(output)
        return adapter.json_schema(), adapter
    raise TypeError(
        "output must be a Pydantic BaseModel type, dataclass type, or JSON schema"
    )


def _final_assistant_text(run_output: RunOutput) -> str | None:
    for message in reversed(run_output.messages or []):
        if message.role != "assistant" or message.from_history or message.tool_calls:
            continue
        if isinstance(message.content, str) and message.content:
            return message.content
    return None


class GenericResponse(Generic[TOutput]):
    def __init__(
        self,
        run_output: RunOutput | None = None,
        stream: AsyncIterator[Any] | None = None,
        structured: bool = False,
        output_adapter: TypeAdapter[Any] | None = None,
    ) -> None:
        self._run_output = run_output
        self._stream = stream
        self._structured = structured
        self._output_adapter = output_adapter
        self._parsed_output: Any = _OUTPUT_UNSET

    @property
    def content(self) -> str | TOutput | None:
        if self._run_output is None:
            return None
        if not self._structured:
            final_text = _final_assistant_text(self._run_output)
            if final_text is not None:
                return final_text
        return self._run_output.content

    @property
    def model(self) -> str | None:
        if self._run_output is not None:
            return self._run_output.model
        return None

    @property
    def output(self) -> TOutput | Any | None:
        if self._run_output is None or not self._structured:
            return None
        if self._parsed_output is not _OUTPUT_UNSET:
            return cast(TOutput | Any | None, self._parsed_output)

        content = self._run_output.content
        try:
            if content is None:
                parsed = None
            elif self._output_adapter is not None:
                parsed = (
                    self._output_adapter.validate_json(content)
                    if isinstance(content, str)
                    else self._output_adapter.validate_python(content)
                )
            elif isinstance(content, str):
                parsed = json.loads(content)
            else:
                parsed = content
        except (ValidationError, json.JSONDecodeError):
            parsed = None

        self._parsed_output = parsed
        return cast(TOutput | Any | None, parsed)

    def __str__(self) -> str:
        content = self.content
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        return str(content)

    def __repr__(self) -> str:
        return f"GenericResponse(content={self.content!r}, is_stream={self.is_stream})"

    @property
    def messages(self) -> list:
        if self._run_output is not None:
            return self._run_output.messages or []
        return []

    @property
    def metrics(self) -> Any:
        if self._run_output is not None:
            return self._run_output.metrics
        return None

    @property
    def tools(self) -> list:
        if self._run_output is not None:
            return self._run_output.tools or []
        return []

    def stream(self) -> AsyncIterator[Any]:
        if self._stream is not None:
            return self._stream
        raise RuntimeError("stream() called on a non-streaming response")

    @property
    def is_stream(self) -> bool:
        return self._stream is not None

    @classmethod
    def from_run_output(
        cls,
        run_output: RunOutput,
        *,
        structured: bool = False,
        output_adapter: TypeAdapter[Any] | None = None,
    ) -> GenericResponse[TOutput]:
        return cls(
            run_output=run_output,
            structured=structured,
            output_adapter=output_adapter,
        )

    @classmethod
    def from_stream(
        cls,
        stream: AsyncIterator[Any],
        *,
        on_finish: Callable[[RunOutput], None] | None = None,
    ) -> GenericResponse[Any]:
        response = cls()

        async def tracked_stream() -> AsyncIterator[Any]:
            async for event in stream:
                if isinstance(event, RunOutput):
                    response._run_output = event
                    if on_finish is not None:
                        on_finish(event)
                    continue
                yield event

        response._stream = tracked_stream()
        return response
