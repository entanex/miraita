from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any

from agno.metrics import ModelMetrics, RunMetrics
from agno.models.message import Message
from agno.models.response import ToolExecution
from agno.run.agent import RunOutput
from arclet.entari import keeping

from miraita.providers.prometheus import Counter, REGISTRY

from .stats import MessageStats, TokenStats, collect_cost, collect_token_stats

if TYPE_CHECKING:
    from .response import GenericResponse


@dataclass(frozen=True, slots=True)
class ModelUsageStats:
    model: str
    tokens: TokenStats
    cost_usd: float


@dataclass(frozen=True, slots=True)
class LLMCallStats:
    model: str
    tokens: TokenStats
    cost_usd: float
    calls: int
    function_calls: int
    functions: list[str]
    model_usage: tuple[ModelUsageStats, ...] = field(
        default_factory=tuple,
        repr=False,
    )

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result.pop("model_usage")
        return result


def _iter_model_metrics(metrics: RunMetrics | None) -> Iterable[ModelMetrics]:
    if metrics is None or not metrics.details:
        return
    for model_metrics in metrics.details.values():
        yield from model_metrics


def _collect_model_usage(
    metrics: RunMetrics | None,
    fallback_model: str,
) -> tuple[ModelUsageStats, ...]:
    usage = tuple(
        ModelUsageStats(
            model=model_metrics.id or fallback_model,
            tokens=collect_token_stats(model_metrics),
            cost_usd=collect_cost(
                model_metrics,
                model_metrics.id or fallback_model,
            ),
        )
        for model_metrics in _iter_model_metrics(metrics)
    )
    if usage or metrics is None:
        return usage
    return (
        ModelUsageStats(
            model=fallback_model,
            tokens=collect_token_stats(metrics),
            cost_usd=collect_cost(metrics, fallback_model),
        ),
    )


def _count_calls(messages: Iterable[Message]) -> int:
    return max(
        1,
        sum(
            1
            for message in messages
            if message.role == "assistant" and not message.from_history
        ),
    )


def _get_functions(
    tools: Iterable[ToolExecution],
    messages: Iterable[Message],
) -> list[str]:
    functions = [str(tool.tool_name or "unknown") for tool in tools]
    if functions:
        return functions

    for message in messages:
        if message.from_history:
            continue
        for tool_call in message.tool_calls or []:
            function = tool_call.get("function") or {}
            functions.append(str(function.get("name") or "unknown"))
    return functions


def collect_llm_call_stats(
    response_obj: RunOutput | GenericResponse[Any],
) -> LLMCallStats:
    metrics = response_obj.metrics
    messages = response_obj.messages or []
    model_usage = _collect_model_usage(metrics, str(response_obj.model or "unknown"))
    model = str(
        response_obj.model or (model_usage[0].model if model_usage else "unknown")
    )
    functions = _get_functions(response_obj.tools or [], messages)
    return LLMCallStats(
        model=model,
        tokens=collect_token_stats(metrics),
        cost_usd=collect_cost(metrics, model),
        calls=_count_calls(messages),
        function_calls=len(functions),
        functions=functions,
        model_usage=model_usage,
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
    llm_call_counter.labels(stats.model).inc(stats.calls)
    usage = stats.model_usage or (
        ModelUsageStats(stats.model, stats.tokens, stats.cost_usd),
    )
    for model_usage in usage:
        for token_type, value in (
            ("input", model_usage.tokens.input),
            ("output", model_usage.tokens.output),
            ("cache_read", model_usage.tokens.cache_read),
            ("cache_write", model_usage.tokens.cache_write),
            ("reasoning", model_usage.tokens.reasoning),
            ("audio_input", model_usage.tokens.audio_input),
            ("audio_output", model_usage.tokens.audio_output),
            ("audio_total", model_usage.tokens.audio_total),
            ("total", model_usage.tokens.total),
        ):
            llm_token_counter.labels(model_usage.model, token_type).inc(value)
        llm_cost_usd_counter.labels(model_usage.model).inc(model_usage.cost_usd)
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
