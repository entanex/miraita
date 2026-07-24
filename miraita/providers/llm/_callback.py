from __future__ import annotations

from typing import TYPE_CHECKING

from agno.run.agent import RunOutput

from .metrics import (
    collect_llm_call_stats,
    record_llm_call_stats,
    record_llm_message_stats,
)
from .stats import collect_message_stats

if TYPE_CHECKING:
    from .service import LLMService


class TokenUsageHandler:
    def __init__(self, service: LLMService):
        self.service = service

    def record(self, run_output: RunOutput) -> None:
        stats = collect_llm_call_stats(run_output)
        self.service.total_tokens += stats.tokens.total
        self.service.total_calls += stats.calls
        record_llm_call_stats(stats)
        record_llm_message_stats(
            stats.model,
            collect_message_stats(run_output.messages),
        )
