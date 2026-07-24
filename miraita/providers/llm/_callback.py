from typing import TYPE_CHECKING

from litellm.integrations.custom_logger import CustomLogger
from .metrics import collect_llm_call_stats, record_llm_call_stats

if TYPE_CHECKING:
    from .service import LLMService


class TokenUsageHandler(CustomLogger):
    def __init__(self, service: "LLMService"):
        self.service = service

    def _record(self, kwargs, response_obj) -> None:
        stats = collect_llm_call_stats(response_obj, kwargs)
        self.service.total_tokens += stats.tokens.total
        self.service.total_calls += 1
        record_llm_call_stats(stats)

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        self._record(kwargs, response_obj)

    async def async_log_stream_event(self, kwargs, response_obj, start_time, end_time):
        self._record(kwargs, response_obj)
