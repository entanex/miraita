from __future__ import annotations

from typing import TYPE_CHECKING

from agno.models.response import ToolExecution
from agno.run.agent import RunOutput

from .log import logger
from .metrics import (
    collect_llm_call_stats,
    record_llm_call_stats,
    record_llm_message_stats,
)
from .stats import collect_message_stats

if TYPE_CHECKING:
    from .service import LLMService


def _format_tool_execution(tool: ToolExecution) -> str:
    name = tool.tool_name or "unknown"
    argument_names = ", ".join(sorted((tool.tool_args or {}).keys()))
    call = f"{name}({argument_names})"
    return f"{call} [failed]" if tool.tool_call_error else call


def _log_tool_executions(run_output: RunOutput) -> None:
    tools = run_output.tools or []
    if not tools:
        return
    calls = " | ".join(_format_tool_execution(tool) for tool in tools)
    logger.debug(f"Tool calls ({len(tools)}): {calls}")


class TokenUsageHandler:
    def __init__(self, service: LLMService):
        self.service = service

    def record(self, run_output: RunOutput) -> None:
        stats = collect_llm_call_stats(run_output)
        _log_tool_executions(run_output)
        self.service.total_tokens += stats.tokens.total
        self.service.total_calls += stats.calls
        record_llm_call_stats(stats)
        record_llm_message_stats(
            stats.model,
            collect_message_stats(run_output.messages),
        )
