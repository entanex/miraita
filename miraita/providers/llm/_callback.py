from typing import TYPE_CHECKING, Any

from litellm.integrations.custom_logger import CustomLogger

from .metrics import (
    llm_call_counter,
    llm_cost_usd_counter,
    llm_function_call_counter,
    llm_token_counter,
    collect_llm_call_stats,
)

if TYPE_CHECKING:
    from .service import LLMService


class TokenUsageHandler(CustomLogger):
    def __init__(self, service: "LLMService"):
        self.service = service

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        self._record(kwargs, response_obj)

    async def async_log_stream_event(self, kwargs, response_obj, start_time, end_time):
        self._record(kwargs, response_obj)

    def _record(self, kwargs: Any, response_obj: Any):
        stats = collect_llm_call_stats(response_obj, kwargs)
        if stats is None:
            return

        self.service.total_tokens += stats.total_tokens
        self.service.prompt_tokens += stats.prompt_tokens
        self.service.completion_tokens += stats.completion_tokens
        self.service.total_calls += 1
        self.service.total_cost_usd += stats.cost_usd
        self.service.total_function_calls += stats.function_calls

        llm_call_counter.labels(stats.model).inc()
        llm_token_counter.labels(stats.model, "prompt").inc(stats.prompt_tokens)
        llm_token_counter.labels(stats.model, "completion").inc(stats.completion_tokens)
        llm_token_counter.labels(stats.model, "total").inc(stats.total_tokens)
        llm_cost_usd_counter.labels(stats.model).inc(stats.cost_usd)

        for function_name in stats.functions:
            llm_function_call_counter.labels(stats.model, function_name).inc()
