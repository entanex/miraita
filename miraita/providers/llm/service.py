import json
from collections.abc import Awaitable, Callable
from typing import Any, Literal, TypeVar, overload

import litellm
from arclet.entari import add_service
from arclet.letoderea.context import generate_contexts
from arclet.letoderea.exceptions import ExitState, _ExitException
from launart import Launart, Service
from launart.status import Phase

from ._callback import TokenUsageHandler
from ._types import Message, ToolMessage
from .config import _conf, get_model_config
from .json_output import OutputType, StructuredModelResponse, parse_output
from .log import logger, log
from .tools.event import LLMToolEvent, available_functions, tools


TOutput = TypeVar("TOutput")


class LLMService(Service):
    id = "entari_plugin_llm"

    def __init__(self):
        super().__init__()
        self.total_tokens = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_calls = 0
        self.total_cost_usd = 0.0
        self.total_function_calls = 0
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
        payload_messages = list(messages)

        if system or conf.prompt:
            payload_messages.insert(
                0, {"role": "system", "content": system or conf.prompt}
            )

        return {
            "model": conf.name,
            "messages": payload_messages,
            "stream": stream,
            "base_url": conf.base_url,
            "api_key": conf.api_key,
            **conf.extra,
            **kwargs,
        }

    async def _handle_tool_call(
        self,
        tool_call: litellm.ChatCompletionMessageToolCall,
    ) -> tuple[ToolMessage | None, bool]:
        function_name = tool_call.function.name
        if function_name is None:
            return None, False

        function_to_call = available_functions[function_name]
        function_args = json.loads(tool_call.function.arguments)
        ctx1 = await generate_contexts(LLMToolEvent())
        logger.debug(f"Calling tool: {function_name} with args: {function_args}")

        exit_loop = False
        try:
            resp = await function_to_call.handle(ctx1 | function_args, inner=True)
            if isinstance(resp, ExitState):
                if resp is ExitState.stop:
                    return None, False
                result = {"ok": True, "data": "已结束对话"}
                exit_loop = True
            elif isinstance(resp, _ExitException):
                result = {"ok": True, "data": resp.args[0] if resp.args else None}
                if len(resp.args) > 1 and resp.args[1]:
                    exit_loop = True
            else:
                result = {"ok": True, "data": resp}
        except Exception as e:
            result = {"ok": False, "error": repr(e)}

        tool_message: ToolMessage = {
            "tool_call_id": tool_call.id,
            "role": "tool",
            "name": function_name,
            "content": json.dumps(result, ensure_ascii=False),
        }
        return tool_message, exit_loop

    @overload
    async def generate(
        self,
        message: str | list[Message],
        *,
        stream: Literal[False] = False,
        system: str | None = None,
        model: str | None = None,
        output: None = None,
        on_message: Callable[[Message], Awaitable[None]] | None = None,
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
        on_message: Callable[[Message], Awaitable[None]] | None = None,
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
        on_message: Callable[[Message], Awaitable[None]] | None = None,
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
        on_message: Callable[[Message], Awaitable[None]] | None = None,
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
        on_message: Callable[[Message], Awaitable[None]] | None = None,
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
        on_message: Callable[[Message], Awaitable[None]] | None = None,
        **kwargs,
    ) -> litellm.ModelResponse | litellm.CustomStreamWrapper:
        if isinstance(message, str):
            messages: list[Message] = [{"role": "user", "content": message}]
        else:
            messages = message

        if output is not None and stream:
            raise ValueError("output is not supported when stream=True")

        if output is not None:
            json_system_hint = (
                "Return valid JSON only. "
                "Do not include markdown code fences or any additional explanation."
            )
            system = f"{system}\n\n{json_system_hint}" if system else json_system_hint

            kwargs["response_format"] = {"type": "json_object"}

        steps = max(1, _conf.toolcall_max_steps)
        for _ in range(steps):
            payload = self._build_payload(
                messages=messages,
                stream=stream,
                system=system,
                model=model,
                tools=tools.copy(),
                tool_choice="auto",
                **kwargs,
            )

            response = await litellm.acompletion(**payload)
            if isinstance(response, litellm.CustomStreamWrapper):
                return response

            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls
            assistant_message: Message = {
                "role": "assistant",
                "content": response_message.content,
            }
            if tool_calls:
                assistant_message["tool_calls"] = [tc.model_dump() for tc in tool_calls]

            messages.append(assistant_message)
            if on_message:
                await on_message(assistant_message)

            if not tool_calls:
                break

            exit_loop = False
            calls = [
                tc
                for tc in tool_calls
                if isinstance(tc, litellm.ChatCompletionMessageToolCall)
            ]
            for tool_call in calls:
                tool_message, should_exit = await self._handle_tool_call(tool_call)
                if tool_message:
                    messages.append(tool_message)
                    if on_message:
                        await on_message(tool_message)
                if should_exit:
                    exit_loop = True
                    break

            if exit_loop:
                response_message["content"] = "[END_OF_RESPONSE]"
                response_message["tool_calls"] = None
                break
        else:
            response = None
            logger.warning("Tool call max steps reached without final response")

        if response is None:
            raise RuntimeError("LLM completion did not return a response")

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

        async with self.stage("blocking"):
            await manager.status.wait_for_sigexit()

        async with self.stage("cleanup"):
            log(
                "success",
                f"| 总请求 [ {self.total_calls} ] "
                f"| 预估总 Token [ {self.total_tokens} ] "
                f"| Function Call [ {self.total_function_calls} ] "
                f"| 预估花费 [ ${self.total_cost_usd:.6f} ]",
            )


llm = LLMService()

add_service(llm)
