from typing import Any, Literal, TypeAlias, TypedDict

from typing_extensions import NotRequired

JSON_VALUE: TypeAlias = str | int | float | bool | None
JSON_TYPE: TypeAlias = dict[str, "JSON_TYPE"] | list["JSON_TYPE"] | JSON_VALUE


class SystemMessage(TypedDict):
    role: Literal["system"]
    content: str
    name: NotRequired[str | None]


class UserMessage(TypedDict):
    role: Literal["user"]
    content: str | list[dict[str, Any]]
    name: NotRequired[str | None]


class AssistantMessage(TypedDict):
    role: Literal["assistant"]
    content: str | None
    tool_calls: NotRequired[list[dict[str, Any]] | None]
    reasoning_content: NotRequired[str | None]


class ToolMessage(TypedDict):
    role: Literal["tool"]
    content: str
    tool_call_id: str


Message: TypeAlias = SystemMessage | UserMessage | AssistantMessage | ToolMessage
