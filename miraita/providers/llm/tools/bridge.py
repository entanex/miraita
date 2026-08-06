"""Bridge Entari LLMToolEvent subscribers to Agno-compatible callables.

Agno expects plain async functions. Entari tools are event subscribers that fire
through the `tools_pub` publisher with provider-injected dependencies. This module
wraps each registered tool so Agno can invoke it, while the Entari event machinery
handles DI and lifecycle.
"""

from collections.abc import Mapping
from copy import deepcopy
import json
from typing import Any
import inspect

from tarina import Empty
from agno.tools.function import Function
from arclet.letoderea.context import generate_contexts
from arclet.letoderea.exceptions import ExitState, _ExitException

from .event import (
    LLMToolEvent,
    LLMToolContext,
    tools_pub,
    registered_tools,
)
from .limit import apply_function_call_limit


def _build_agno_tool(name: str, context: LLMToolContext) -> Function:
    """Create an Agno Function for a named Entari tool."""

    registration = registered_tools[name]
    sub = registration.subscriber

    async def _wrapper(**kwargs: Any) -> str:
        event = LLMToolEvent(arguments=kwargs, context=context)
        tool_ctx = await generate_contexts(event, tools_pub.supplier)

        try:
            resp = await sub.handle(tool_ctx)
            if isinstance(resp, ExitState):
                if resp is ExitState.stop:
                    return json.dumps(
                        {"ok": True, "data": "已结束对话"}, ensure_ascii=False
                    )
                return json.dumps({"ok": True, "data": str(resp)}, ensure_ascii=False)
            if isinstance(resp, _ExitException):
                result = {"ok": True, "data": resp.args[0] if resp.args else None}
                return json.dumps(result, ensure_ascii=False)
            validated = event.check_result(resp)
            if validated is None:
                raise TypeError(f"工具 {name} 返回值不是 JSON 兼容类型")
            return json.dumps({"ok": True, "data": validated.value}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": repr(e)}, ensure_ascii=False)

    _wrapper.__name__ = name
    _wrapper.__doc__ = sub.__doc__ or ""

    parameters: list[inspect.Parameter] = []
    annotations: dict[str, Any] = {"return": str}
    for param in registration.parameters:
        annotations[param.name] = param.annotation
        parameters.append(
            inspect.Parameter(
                name=param.name,
                kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                default=(
                    inspect.Parameter.empty if param.default is Empty else param.default
                ),
                annotation=param.annotation,
            )
        )
    _wrapper.__annotations__ = annotations
    setattr(
        _wrapper, "__signature__", inspect.Signature(parameters, return_annotation=str)
    )

    instructions = registration.instructions
    schema = registration.schema["function"]
    return Function(
        name=name,
        description=schema["description"],
        parameters=deepcopy(schema["parameters"]),
        instructions=instructions,
        entrypoint=_wrapper,
    )


def get_agno_tools(
    context: LLMToolContext | None = None,
    call_limits: Mapping[str, int] | None = None,
) -> list[Function]:
    """Return all registered Entari tools as Agno Functions."""
    tool_context = context or LLMToolContext()
    functions: list[Function] = []
    functions_by_plugin: dict[str, list[Function]] = {}

    for name, registration in registered_tools.items():
        function = _build_agno_tool(name, tool_context)
        functions.append(function)
        functions_by_plugin.setdefault(registration.plugin_id, []).append(function)

    for plugin_id, plugin_functions in functions_by_plugin.items():
        if call_limits is not None and (call_limit := call_limits.get(plugin_id)):
            apply_function_call_limit(plugin_functions, plugin_id, call_limit)

    return functions
