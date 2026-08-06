from collections.abc import Callable, Iterable, Mapping
from inspect import iscoroutinefunction, signature
from typing import Any

from agno.exceptions import AgentRunException
from agno.tools.function import Function

CALL_LIMIT_OPTION = "$call_limit"


def get_call_limit(label: str, options: Mapping[str, Any]) -> int | None:
    value = options.get(CALL_LIMIT_OPTION)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"工具 {label!r} 的 {CALL_LIMIT_OPTION} 必须是正整数")
    return value


def resolve_call_limits(
    configs: Mapping[str, Mapping[str, Any]] | None,
) -> dict[str, int]:
    if configs is None:
        return {}

    limits: dict[str, int] = {}
    for label, options in configs.items():
        if label.startswith("$"):
            continue
        if not isinstance(options, Mapping):
            raise TypeError(f"工具 {label!r} 的配置必须是映射")
        if (call_limit := get_call_limit(label, options)) is not None:
            limits[label] = call_limit
    return limits


def _wrap_pre_hook(
    previous: Callable[..., Any] | None,
    guard: Callable[[], None],
) -> Callable[..., Any]:
    if previous is None:
        return guard

    parameters = signature(previous).parameters

    def previous_arguments(
        agent: Any,
        team: Any,
        run_context: Any,
        fc: Any,
    ) -> dict[str, Any]:
        available = {
            "agent": agent,
            "team": team,
            "run_context": run_context,
            "fc": fc,
        }
        return {name: available[name] for name in available if name in parameters}

    if iscoroutinefunction(previous):

        async def async_hook(
            agent: Any = None,
            team: Any = None,
            run_context: Any = None,
            fc: Any = None,
        ) -> Any:
            guard()
            return await previous(**previous_arguments(agent, team, run_context, fc))

        return async_hook

    def sync_hook(
        agent: Any = None,
        team: Any = None,
        run_context: Any = None,
        fc: Any = None,
    ) -> Any:
        guard()
        return previous(**previous_arguments(agent, team, run_context, fc))

    return sync_hook


def apply_function_call_limit(
    functions: Iterable[Function],
    label: str,
    call_limit: int,
) -> None:
    call_count = 0
    limit_message = (
        f"Tool call limit ({call_limit}) reached for {label}. "
        "This call was not executed. Use the existing results and do not call "
        "tools from this group again."
    )

    def guard() -> None:
        nonlocal call_count
        if call_count >= call_limit:
            raise AgentRunException(limit_message)
        call_count += 1

    seen: set[int] = set()
    for function in functions:
        identity = id(function)
        if identity in seen:
            continue
        seen.add(identity)
        function.pre_hook = _wrap_pre_hook(function.pre_hook, guard)
