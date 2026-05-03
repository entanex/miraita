import inspect
from typing import Annotated, Any, get_args

from arclet.entari import MessageCreatedEvent
from arclet.letoderea import Subscriber, define
from arclet.letoderea.provider import get_providers
from arclet.letoderea.typing import Result
from docstring_parser import parse
from tarina import Empty
from tarina.generic import get_origin, origin_is_union
from typing_extensions import Doc

from .._types import JSON_TYPE

mapping = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    set: "array",
    tuple: "array",
    dict: "object",
}


class LLMToolEvent:
    __publisher__ = "tools_pub"

    def check_result(self, value: Any) -> Result[JSON_TYPE] | None:
        if isinstance(value, str | int | float | bool | type(None) | list | dict):
            return Result(value)


tools_pub = define(LLMToolEvent, name="tools_pub")
tools_pub.providers.extend(get_providers(MessageCreatedEvent))


tools = []
available_functions: dict[str, Subscriber[JSON_TYPE]] = {}


@tools_pub.check
def _register_tool(_, sub: Subscriber):
    properties = {}
    required = []
    doc = inspect.cleandoc(sub.__doc__ or "")

    parsed = parse(doc)
    param_docs = {p.arg_name: p.description or "" for p in parsed.params}

    for param in sub.params:
        if param.providers:  # skip provided parameters
            continue
        if param.default is Empty:
            required.append(param.name)
        anno = param.annotation
        orig = get_origin(anno)
        if origin_is_union(orig) and type(None) in get_args(anno):  # pragma: no cover
            t = get_args(anno)[0]
        else:
            t = anno
        documentation = param_docs.get(param.name, "")
        if get_origin(t) is Annotated:  # pragma: no cover
            t, *meta = get_args(t)
            if doc := next((i for i in meta if isinstance(i, Doc)), None):
                documentation = doc.documentation
        properties[param.name] = {
            "title": param.name.title(),
            "type": mapping.get(get_origin(t), "object"),
            "description": documentation,
        }

    tools.append(
        {
            "type": "function",
            "function": {
                "name": sub.__name__,
                "description": parsed.description or doc,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                    "additionalProperties": False,
                },
            },
        }
    )
    available_functions[sub.__name__] = sub
    sub._attach_disposes(lambda s: available_functions.pop(s.__name__, None))  # type: ignore
    return True
