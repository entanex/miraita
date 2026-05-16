from typing import Any
from dataclasses import asdict, dataclass

import litellm
from arclet.entari import keeping

from miraita.providers.prometheus import Counter, REGISTRY


def _get_value(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _get_usage(response_obj: Any) -> dict[str, int]:
    usage = _get_value(response_obj, "usage") or {}
    prompt_tokens = int(_get_value(usage, "prompt_tokens", 0) or 0)
    completion_tokens = int(_get_value(usage, "completion_tokens", 0) or 0)
    total_tokens = int(_get_value(usage, "total_tokens", 0) or 0)
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens or prompt_tokens + completion_tokens,
    }


def _get_model(kwargs: Any, response_obj: Any) -> str:
    model = _get_value(response_obj, "model") or _get_value(kwargs, "model")
    return str(model or "unknown")


def _iter_tool_calls(response_obj: Any):
    choices = _get_value(response_obj, "choices", []) or []
    for choice in choices:
        message = _get_value(choice, "message") or {}
        tool_calls = _get_value(message, "tool_calls", []) or []
        yield from tool_calls


def _get_function_name(tool_call: Any) -> str:
    function = _get_value(tool_call, "function") or {}
    name = _get_value(function, "name")
    return str(name or "unknown")


def _calculate_cost(response_obj: Any, model: str) -> float:
    try:
        return float(
            litellm.completion_cost(
                completion_response=response_obj,
                model=model,
            )
            or 0
        )
    except Exception:
        return 0.0


@dataclass
class LLMCallStats:
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    function_calls: int
    functions: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def collect_llm_call_stats(
    response_obj: Any,
    kwargs: Any | None = None,
) -> LLMCallStats | None:
    usage = _get_usage(response_obj)
    if usage["total_tokens"] <= 0:
        return None

    model = _get_model(kwargs or {}, response_obj)
    functions = [
        _get_function_name(tool_call) for tool_call in _iter_tool_calls(response_obj)
    ]

    return LLMCallStats(
        model=model,
        prompt_tokens=usage["prompt_tokens"],
        completion_tokens=usage["completion_tokens"],
        total_tokens=usage["total_tokens"],
        cost_usd=_calculate_cost(response_obj, model),
        function_calls=len(functions),
        functions=functions,
    )


llm_call_counter = keeping(
    "llm_call_counter",
    obj_factory=lambda: Counter(
        "miraita_llm_calls",
        "Total number of LLM calls",
        ["model"],
    ),
    dispose=lambda counter: REGISTRY.unregister(counter),
)

llm_token_counter = keeping(
    "llm_token_counter",
    obj_factory=lambda: Counter(
        "miraita_llm_tokens",
        "Total number of LLM tokens",
        ["model", "token_type"],
    ),
    dispose=lambda counter: REGISTRY.unregister(counter),
)

llm_cost_usd_counter = keeping(
    "llm_cost_usd_counter",
    obj_factory=lambda: Counter(
        "miraita_llm_cost_usd",
        "Estimated total cost of LLM calls in USD",
        ["model"],
    ),
    dispose=lambda counter: REGISTRY.unregister(counter),
)

llm_function_call_counter = keeping(
    "llm_function_call_counter",
    obj_factory=lambda: Counter(
        "miraita_llm_function_calls",
        "Total number of LLM requested function calls",
        ["model", "function_name"],
    ),
    dispose=lambda counter: REGISTRY.unregister(counter),
)
