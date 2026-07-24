from collections.abc import Iterable
from dataclasses import dataclass, field

import litellm
from agno.metrics import BaseMetrics, ModelMetrics
from agno.models.message import Message


def _iter_model_metrics(source: BaseMetrics) -> Iterable[ModelMetrics]:
    details = getattr(source, "details", None)
    if not details:
        return
    for model_metrics in details.values():
        yield from model_metrics


def _estimate_cost(model: str, metrics: BaseMetrics) -> float:
    if not model:
        return 0.0
    try:
        input_cost, output_cost = litellm.cost_per_token(
            model=model,
            prompt_tokens=metrics.input_tokens,
            completion_tokens=metrics.output_tokens,
            cache_creation_input_tokens=metrics.cache_write_tokens,
            cache_read_input_tokens=metrics.cache_read_tokens,
        )
    except Exception:
        return 0.0
    return float(input_cost + output_cost)


@dataclass(frozen=True, slots=True)
class MessageStats:
    user: int = 0
    assistant: int = 0
    tool_calls: int = 0
    tool_results: int = 0
    total: int = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "total",
            self.user + self.assistant + self.tool_calls + self.tool_results,
        )


@dataclass(frozen=True, slots=True)
class TokenStats:
    input: int = 0
    output: int = 0
    cache_read: int = 0
    cache_write: int = 0
    reasoning: int = 0
    audio_input: int = 0
    audio_output: int = 0
    audio_total: int = 0
    total: int = 0


def collect_message_stats(messages: Iterable[Message] | None) -> MessageStats:
    user = 0
    assistant = 0
    tool_calls = 0
    tool_results = 0

    for message in messages or ():
        if message.from_history:
            continue

        calls = message.tool_calls or []
        call_count = len(calls)

        if message.role == "user":
            user += 1
        elif message.role == "assistant":
            assistant += 1
        elif message.role == "tool":
            tool_results += call_count or 1

        tool_calls += call_count

    return MessageStats(
        user=user,
        assistant=assistant,
        tool_calls=tool_calls,
        tool_results=tool_results,
    )


def collect_token_stats(source: BaseMetrics | None) -> TokenStats:
    if source is None:
        return TokenStats()

    input_tokens = source.input_tokens or 0
    output_tokens = source.output_tokens or 0
    audio_input_tokens = source.audio_input_tokens or 0
    audio_output_tokens = source.audio_output_tokens or 0
    return TokenStats(
        input=input_tokens,
        output=output_tokens,
        cache_read=source.cache_read_tokens or 0,
        cache_write=source.cache_write_tokens or 0,
        reasoning=source.reasoning_tokens or 0,
        audio_input=audio_input_tokens,
        audio_output=audio_output_tokens,
        audio_total=source.audio_total_tokens
        or audio_input_tokens + audio_output_tokens,
        total=source.total_tokens or input_tokens + output_tokens,
    )


def collect_cost(source: BaseMetrics | None, model: str | None = None) -> float:
    if source is None:
        return 0.0
    if source.cost is not None:
        return float(source.cost)

    model_metrics = list(_iter_model_metrics(source))
    if model_metrics:
        return sum(
            float(metrics.cost)
            if metrics.cost is not None
            else _estimate_cost(metrics.id, metrics)
            for metrics in model_metrics
        )
    return _estimate_cost(model or "", source)


def collect_session_usage(
    metrics: BaseMetrics | None,
    model: str | None = None,
) -> tuple[TokenStats, float]:
    return collect_token_stats(metrics), collect_cost(metrics, model)
