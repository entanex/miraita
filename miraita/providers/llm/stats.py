from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any


def _get_value(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _to_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _first_int(obj: Any, *keys: str) -> int:
    fallback = 0
    for key in keys:
        value = _get_value(obj, key)
        if value is None:
            continue
        parsed = _to_int(value)
        if parsed:
            return parsed
        fallback = parsed
    return fallback


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
    total: int = 0


def collect_message_stats(messages: Iterable[Any] | None) -> MessageStats:
    user = 0
    assistant = 0
    tool_calls = 0
    tool_results = 0

    for message in messages or ():
        if _get_value(message, "from_history", False):
            continue

        role = str(_get_value(message, "role", "") or "")
        calls = _get_value(message, "tool_calls", []) or []
        call_count = len(calls)

        if role == "user":
            user += 1
        elif role == "assistant":
            assistant += 1
        elif role == "tool":
            tool_results += call_count or 1

        tool_calls += call_count

    return MessageStats(
        user=user,
        assistant=assistant,
        tool_calls=tool_calls,
        tool_results=tool_results,
    )


def collect_token_stats(source: Any) -> TokenStats:
    input_tokens = _first_int(source, "input_tokens", "prompt_tokens")
    output_tokens = _first_int(source, "output_tokens", "completion_tokens")
    cache_read_tokens = _first_int(
        source,
        "cache_read_tokens",
        "cache_read_input_tokens",
        "cached_tokens",
    )

    if not cache_read_tokens:
        details = _get_value(source, "input_tokens_details") or _get_value(
            source,
            "prompt_tokens_details",
        )
        cache_read_tokens = _first_int(
            details or {},
            "cached_tokens",
            "cache_read_tokens",
        )

    total_tokens = _first_int(source, "total_tokens")
    if not total_tokens:
        total_tokens = input_tokens + output_tokens

    return TokenStats(
        input=input_tokens,
        output=output_tokens,
        cache_read=cache_read_tokens,
        total=total_tokens,
    )


def collect_cost(source: Any) -> float:
    for key in ("cost", "cost_usd", "response_cost"):
        value = _get_value(source, key)
        if value is None:
            continue
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            continue
    return 0.0


def collect_session_usage(session: Any) -> tuple[TokenStats, float]:
    session_data = _get_value(session, "session_data") or {}
    session_metrics = _get_value(session_data, "session_metrics")
    if session_metrics:
        sources = [session_metrics]
    else:
        sources = [
            metrics
            for run in (_get_value(session, "runs") or [])
            if (metrics := _get_value(run, "metrics")) is not None
        ]

    input_tokens = 0
    output_tokens = 0
    cache_read_tokens = 0
    total_tokens = 0
    cost_usd = 0.0

    for source in sources:
        tokens = collect_token_stats(source)
        input_tokens += tokens.input
        output_tokens += tokens.output
        cache_read_tokens += tokens.cache_read
        total_tokens += tokens.total
        cost_usd += collect_cost(source)

    return (
        TokenStats(
            input=input_tokens,
            output=output_tokens,
            cache_read=cache_read_tokens,
            total=total_tokens,
        ),
        cost_usd,
    )
