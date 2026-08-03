from typing import Any, Annotated, TypeAlias, cast, get_args, overload
import inspect
from dataclasses import field, dataclass
from collections.abc import Mapping, Callable, Awaitable
from typing_extensions import Doc

from tarina import Empty
from arclet.entari import MessageChain, MessageCreatedEvent
from tarina.generic import get_origin, origin_is_union
from arclet.letoderea import (
    EVENT,
    STACK,
    RESULT,
    SUBSCRIBER,
    Param,
    CtxItem,
    Contexts,
    Provider,
    Subscriber,
    define,
)
from docstring_parser import parse
from arclet.entari.const import ITEM_MESSAGE_CONTENT
from arclet.entari.plugin import get_plugin
from arclet.letoderea.utils import Result
from arclet.letoderea.provider import get_providers
from arclet.entari.config.dc_schema import _MISSING, SchemaGenerator

from ..log import logger

JSON_VALUE: TypeAlias = str | int | float | bool | None
JSON_TYPE: TypeAlias = dict[str, "JSON_TYPE"] | list["JSON_TYPE"] | JSON_VALUE

ToolCallable: TypeAlias = Callable[..., Any]


@dataclass(frozen=True, slots=True)
class LLMToolContext:
    user_message: MessageChain | None = None
    variables: Mapping[str, Any] = field(default_factory=dict)
    dependencies: Mapping[str, Any] = field(default_factory=dict)


_RUNTIME_CONTEXT_KEYS = frozenset({EVENT, RESULT, STACK, SUBSCRIBER, "$depend_cache"})
LLM_TOOL_CONTEXT = CtxItem[LLMToolContext].make("$llm_tool_context")


def snapshot_tool_dependencies(context: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value for key, value in context.items() if key not in _RUNTIME_CONTEXT_KEYS
    }


def resolve_tool_context(
    context: LLMToolContext | None,
    variables: Mapping[str, Any] | None = None,
) -> LLMToolContext:
    if context is None:
        return LLMToolContext(variables=variables or {})

    context_variables = dict(context.variables)
    context_variables.update(variables or {})
    return LLMToolContext(
        user_message=context.user_message,
        variables=context_variables,
        dependencies=context.dependencies,
    )


def llm_variable(name: str) -> Callable[[Contexts], Awaitable[Any]]:
    async def resolve(context: Contexts) -> Any:
        tool_context = context.get(LLM_TOOL_CONTEXT)
        if tool_context is None:
            return None
        return tool_context.variables.get(name)

    return resolve


ToolInstructions: TypeAlias = str
_TOOL_INSTRUCTIONS_ATTR = "__llm_tool_instructions__"


def _is_json_type(value: Any) -> bool:
    if value is None or isinstance(value, (str, int, float, bool)):
        return True
    if isinstance(value, list):
        return all(_is_json_type(item) for item in value)
    if isinstance(value, dict):
        return all(
            isinstance(key, str) and _is_json_type(item) for key, item in value.items()
        )
    return False


@dataclass(frozen=True, slots=True)
class LLMToolEvent:
    arguments: Mapping[str, Any]
    context: LLMToolContext

    def check_result(self, value: Any) -> Result[JSON_TYPE] | None:
        if _is_json_type(value):
            return Result(cast(JSON_TYPE, value))


class LLMToolContextProvider(Provider[LLMToolContext]):
    async def __call__(self, context: Contexts) -> LLMToolContext | None:
        return context.get(LLM_TOOL_CONTEXT)


tools_pub = define(LLMToolEvent, name="tools_pub")
tools_pub.providers.extend(
    [*get_providers(MessageCreatedEvent), LLMToolContextProvider()]
)


@tools_pub.gather
async def gather_tool_context(event: LLMToolEvent, context: Contexts) -> None:
    context.update(event.context.dependencies)
    context[LLM_TOOL_CONTEXT] = event.context
    if event.context.user_message is not None:
        context[ITEM_MESSAGE_CONTENT] = event.context.user_message
    context.update(event.arguments)


@dataclass(frozen=True, slots=True)
class RegisteredTool:
    subscriber: Subscriber[Any]
    schema: dict[str, Any]
    parameters: tuple[Param, ...]
    instructions: ToolInstructions | None


registered_tools: dict[str, RegisteredTool] = {}
_generator = SchemaGenerator()


@overload
def llm_tool(func: ToolCallable, /) -> Subscriber[Any]: ...


@overload
def llm_tool(
    *,
    instructions: ToolInstructions | None = None,
) -> Callable[[ToolCallable], Subscriber[Any]]: ...


def llm_tool(
    func: ToolCallable | None = None,
    /,
    *,
    instructions: ToolInstructions | None = None,
) -> Subscriber[Any] | Callable[[ToolCallable], Subscriber[Any]]:
    """Register a model-callable tool.

    Put capability, accepted inputs, and exclusions in the function docstring: that
    description is only exposed when the tool is actually loaded. Reserve
    ``instructions`` for this tool's unconditional runtime rules; never use it to route
    to another optionally configured tool.
    """
    dispatcher = get_plugin(1).dispatch(LLMToolEvent)

    def register(target: ToolCallable) -> Subscriber[Any]:
        if instructions is not None:
            setattr(target, _TOOL_INSTRUCTIONS_ATTR, instructions)
        return cast(Subscriber[Any], dispatcher(target))

    return register(func) if func is not None else register


def _resolve_parameter_schema(
    param: Param,
    documentation: str,
) -> tuple[Any, str]:
    annotation = param.annotation
    if get_origin(annotation) is Annotated:  # pragma: no cover
        annotation, *metadata = get_args(annotation)
        annotation_doc = next(
            (item for item in metadata if isinstance(item, Doc)),
            None,
        )
        if annotation_doc is not None:
            documentation = annotation_doc.documentation

    args = get_args(annotation)
    if origin_is_union(get_origin(annotation)) and type(None) in args:
        non_none = tuple(item for item in args if item is not type(None))
        if len(non_none) == 1:
            annotation = non_none[0]
    return annotation, documentation


@tools_pub.check
def _register_tool(_, sub: Subscriber[Any]):
    docstring = inspect.cleandoc(sub.__doc__ or "")
    parsed = parse(docstring)
    param_docs = {param.arg_name: param.description or "" for param in parsed.params}
    parameters = tuple(
        param for param in sub.params if not param.providers and not param.depend
    )
    properties: dict[str, Any] = {}
    required: list[str] = []

    for param in parameters:
        if param.default is Empty:
            required.append(param.name)
        annotation, documentation = _resolve_parameter_schema(
            param,
            param_docs.get(param.name, ""),
        )
        properties[param.name] = {
            **_generator.get_field_schema(annotation, _MISSING),
            "title": param.name.title(),
            "description": documentation,
        }

    tool_schema = {
        "type": "function",
        "function": {
            "name": sub.__name__,
            "description": parsed.description or docstring,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": False,
            },
        },
    }
    instructions = getattr(sub.callable_target, _TOOL_INSTRUCTIONS_ATTR, None)
    if not isinstance(instructions, str):
        instructions = None

    name = sub.__name__
    registered_tools[name] = RegisteredTool(
        subscriber=sub,
        schema=tool_schema,
        parameters=parameters,
        instructions=instructions,
    )

    def dispose_tool(current: Subscriber[Any]) -> None:
        registered = registered_tools.get(name)
        if registered is not None and registered.subscriber is current:
            registered_tools.pop(name, None)

    sub._attach_disposes(dispose_tool)
    logger.debug(f"Registered tool: {name}")
    return True
