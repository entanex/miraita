from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeAlias, cast, overload

from agno.models.message import Message
from arclet.entari.plugin import get_plugin
from arclet.letoderea import Contexts, Result, Subscriber, define, waterfall

from .tools.event import LLMToolContext

LLMContextMessage: TypeAlias = Message | list[Message]
ContextCallable: TypeAlias = Callable[..., Any]


@dataclass(frozen=True, slots=True)
class LLMBuildContextEvent:
    tool_context: LLMToolContext

    def check_result(self, value: Any) -> Result[LLMContextMessage] | None:
        if isinstance(value, Message):
            return Result(value)
        if isinstance(value, list) and all(isinstance(item, Message) for item in value):
            return Result(value)


context_pub = define(LLMBuildContextEvent, name="llm/build_context")


@context_pub.gather
async def gather_context_event(
    event: LLMBuildContextEvent,
    context: Contexts,
) -> None:
    context["tool_context"] = event.tool_context


@overload
def llm_context(func: ContextCallable, /) -> Subscriber[Any]: ...


@overload
def llm_context(
    *,
    priority: int = 16,
) -> Callable[[ContextCallable], Subscriber[Any]]: ...


def llm_context(
    func: ContextCallable | None = None,
    /,
    *,
    priority: int = 16,
) -> Subscriber[Any] | Callable[[ContextCallable], Subscriber[Any]]:
    dispatcher = get_plugin(1).dispatch(LLMBuildContextEvent)

    def register(target: ContextCallable) -> Subscriber[Any]:
        return cast(Subscriber[Any], dispatcher.register(target, priority=priority))

    return register(func) if func is not None else register


async def build_context_messages(context: LLMToolContext) -> list[Message]:
    event = LLMBuildContextEvent(tool_context=context)
    messages: list[Message] = []
    async for result in waterfall(event):
        validated = event.check_result(result.value)
        if validated is None:
            raise TypeError(
                "LLM context subscribers must return Message, list[Message], or None"
            )
        if isinstance(validated.value, Message):
            messages.append(validated.value)
        else:
            messages.extend(validated.value)
    return messages


async def inject_context_messages(
    message: str | list[Message],
    context: LLMToolContext,
) -> str | list[Message]:
    context_messages = await build_context_messages(context)
    if not context_messages:
        return message
    if isinstance(message, list):
        return [*context_messages, *message]
    return [*context_messages, Message(role="user", content=message)]
