from dataclasses import asdict, dataclass
from typing import Any

import litellm
from arclet.entari import keeping

from miraita.providers.prometheus import Counter, REGISTRY

from .stats import MessageStats, TokenStats, collect_cost, collect_token_stats


def _get_value(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _get_usage(response_obj: Any) -> TokenStats:
    metrics = _get_value(response_obj, "metrics")
    if metrics is not None:
        return collect_token_stats(metrics)
    usage = _get_value(response_obj, "usage") or {}
    return collect_token_stats(usage)


def _get_model(kwargs: Any, response_obj: Any) -> str:
    model = _get_value(response_obj, "model") or _get_value(kwargs, "model")
    return str(model or "unknown")


def _iter_tool_calls(response_obj: Any):
    choices = _get_value(response_obj, "choices", []) or []
    if choices:
        for choice in choices:
            message = _get_value(choice, "message") or {}
            tool_calls = _get_value(message, "tool_calls", []) or []
            yield from tool_calls
        return

    for message in _get_value(response_obj, "messages", []) or []:
        if _get_value(message, "from_history", False):
            continue
        tool_calls = _get_value(message, "tool_calls", []) or []
        yield from tool_calls


def _get_function_name(tool_call: Any) -> str:
    function = _get_value(tool_call, "function") or {}
    name = _get_value(function, "name")
    return str(name or "unknown")


def _calculate_cost(response_obj: Any, model: str) -> float:
    metrics = _get_value(response_obj, "metrics")
    usage = _get_value(response_obj, "usage") or {}
    hidden_params = _get_value(response_obj, "_hidden_params") or {}
    for source in (metrics, usage, hidden_params, response_obj):
        cost = collect_cost(source)
        if cost:
            return cost

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


@dataclass(frozen=True, slots=True)
class LLMCallStats:
    model: str
    tokens: TokenStats
    cost_usd: float
    function_calls: int
    functions: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def collect_llm_call_stats(
    response_obj: Any,
    kwargs: Any | None = None,
) -> LLMCallStats:
    model = _get_model(kwargs or {}, response_obj)
    functions = [
        _get_function_name(tool_call) for tool_call in _iter_tool_calls(response_obj)
    ]
    return LLMCallStats(
        model=model,
        tokens=_get_usage(response_obj),
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

llm_message_counter = keeping(
    "llm_message_counter",
    obj_factory=lambda: Counter(
        "miraita_llm_messages",
        "Total number of LLM session messages",
        ["model", "message_type"],
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


def record_llm_call_stats(stats: LLMCallStats) -> None:
    llm_call_counter.labels(stats.model).inc()
    for token_type, value in (
        ("input", stats.tokens.input),
        ("output", stats.tokens.output),
        ("cache_read", stats.tokens.cache_read),
        ("total", stats.tokens.total),
    ):
        llm_token_counter.labels(stats.model, token_type).inc(value)
    llm_cost_usd_counter.labels(stats.model).inc(stats.cost_usd)
    for function_name in stats.functions:
        llm_function_call_counter.labels(stats.model, function_name).inc()


def record_llm_message_stats(model: str, stats: MessageStats) -> None:
    for message_type, value in (
        ("user", stats.user),
        ("assistant", stats.assistant),
        ("tool_call", stats.tool_calls),
        ("tool_result", stats.tool_results),
    ):
        llm_message_counter.labels(model, message_type).inc(value)
