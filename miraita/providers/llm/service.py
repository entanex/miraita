import time
from typing import Any, Literal, TypeVar, overload

import litellm
from arclet.entari import add_service
from launart import Launart, Service
from launart.status import Phase

from miraita.providers.prometheus import get_system_metrics  # entari: plugin

from .tools.event import tools
from ._callback import TokenUsageHandler
from ._types import Message
from .config import get_model_config
from .json_output import OutputType, StructuredModelResponse, parse_output
from .log import log


TOutput = TypeVar("TOutput")


class LLMService(Service):
    id = "entari_plugin_llm"

    def __init__(self):
        super().__init__()
        self.total_tokens = 0
        self.total_calls = 0
        self.usage_handler = TokenUsageHandler(self)

    @property
    def required(self) -> set[str]:
        return set()

    @property
    def stages(self) -> set[Phase]:
        return {"preparing", "blocking", "cleanup"}

    def _build_payload(
        self,
        messages: list[Message],
        stream: bool,
        system: str | None = None,
        model: str | None = None,
        **kwargs,
    ) -> dict:
        conf = get_model_config(model)

        if system or conf.prompt:
            messages.insert(0, {"role": "system", "content": system or conf.prompt})

        return {
            "model": conf.name,
            "messages": messages,
            "stream": stream,
            "base_url": conf.base_url,
            "api_key": conf.api_key,
            **conf.extra,
            **kwargs,
        }

    @overload
    async def generate(
        self,
        message: str | list[Message],
        *,
        stream: Literal[False] = False,
        system: str | None = None,
        model: str | None = None,
        output: None = None,
        **kwargs,
    ) -> litellm.ModelResponse: ...

    @overload
    async def generate(
        self,
        message: str | list[Message],
        *,
        stream: Literal[True],
        system: str | None = None,
        model: str | None = None,
        output: None = None,
        **kwargs,
    ) -> litellm.CustomStreamWrapper: ...

    @overload
    async def generate(
        self,
        message: str | list[Message],
        *,
        stream: Literal[False] = False,
        system: str | None = None,
        model: str | None = None,
        output: Literal["json_object"] | dict[str, Any],
        **kwargs,
    ) -> StructuredModelResponse[Any]: ...

    @overload
    async def generate(
        self,
        message: str | list[Message],
        *,
        stream: Literal[False] = False,
        system: str | None = None,
        model: str | None = None,
        output: type[TOutput],
        **kwargs,
    ) -> StructuredModelResponse[TOutput]: ...

    @overload
    async def generate(
        self,
        message: str | list[Message],
        *,
        stream: bool,
        system: str | None = None,
        model: str | None = None,
        output: OutputType | None = None,
        **kwargs,
    ) -> litellm.ModelResponse | litellm.CustomStreamWrapper: ...

    async def generate(
        self,
        message: str | list[Message],
        *,
        stream: bool = False,
        system: str | None = None,
        model: str | None = None,
        output: OutputType | None = None,
        **kwargs,
    ) -> litellm.ModelResponse | litellm.CustomStreamWrapper:
        if isinstance(message, str):
            message = [{"role": "user", "content": message}]

        if output is not None and stream:
            raise ValueError("output is not supported when stream=True")

        if output is not None:
            json_system_hint = (
                "Return valid JSON only. "
                "Do not include markdown code fences or any additional explanation."
            )
            system = f"{system}\n\n{json_system_hint}" if system else json_system_hint

            kwargs["response_format"] = {"type": "json_object"}

        payload = self._build_payload(
            messages=message,
            stream=stream,
            system=system,
            model=model,
            tools=tools,
            tool_choice="auto",
            **kwargs,
        )

        response = await litellm.acompletion(**payload)

        if output is not None:
            if isinstance(response, litellm.CustomStreamWrapper):
                raise ValueError("output is not supported when stream=True")

            content = response.choices[0].message.content
            parsed = parse_output(content, output)
            return StructuredModelResponse.from_model_response(response, parsed)

        return response

    async def vision(
        self,
        image_url: str,
        *,
        system: str | None = None,
        model: str | None = None,
    ) -> litellm.ModelResponse:
        image_payload = (
            {"url": image_url} if isinstance(image_url, str) else image_url["image_url"]
        )
        message: list[Message] = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What’s in this image?"},
                    {"type": "image_url", "image_url": image_payload},
                ],
            }
        ]

        conf = get_model_config(model)

        if not litellm.supports_vision(conf.name):
            raise RuntimeError(f"Model {conf.name} does not support vision input")

        return await self.generate(message, system=system, model=conf.name)

    async def launch(self, manager: Launart):
        async with self.stage("preparing"):
            litellm.drop_params = True
            litellm.callbacks = [self.usage_handler]
            self.start_time = time.time()

        async with self.stage("blocking"):
            await manager.status.wait_for_sigexit()

        async with self.stage("cleanup"):
            uptime = get_system_metrics().uptime
            log(
                "success",
                f"运行统计: 耗时 [ {uptime} ] "
                f"| 总请求 [ {self.total_calls} ] "
                f"| 预估总 Token [ {self.total_tokens} ]",
            )


llm = LLMService()

add_service(llm)
