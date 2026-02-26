from typing import TYPE_CHECKING

from litellm.integrations.custom_logger import CustomLogger

if TYPE_CHECKING:
    from .service import LLMService


class TokenUsageHandler(CustomLogger):
    def __init__(self, service: "LLMService"):
        self.service = service

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        if "usage" in response_obj:
            self.service.total_tokens += response_obj["usage"].get("total_tokens", 0)
            self.service.total_calls += 1

    async def async_log_stream_event(self, kwargs, response_obj, start_time, end_time):
        if "usage" in response_obj:
            self.service.total_tokens += response_obj["usage"].get("total_tokens", 0)
            self.service.total_calls += 1
