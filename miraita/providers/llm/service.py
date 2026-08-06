import time
from typing import Any, Literal, TypeVar, overload

from launart import Launart, Service
import litellm
from agno.agent import Agent
from agno.memory import MemoryManager
from agno.run.base import RunStatus
from arclet.entari import local_data, add_service
from agno.db.sqlite import AsyncSqliteDb
from launart.status import Phase
from agno.models.litellm import LiteLLM
from agno.models.message import Message
from agno.db.schemas.memory import UserMemory
from entari_plugin_user.models import UserSession

from .config import _conf, get_model_config
from .memory import memory_settings
from .context import inject_context_messages
from .session import SessionInfo, AgnoSessionStore
from .response import GenericResponse, prepare_output_schema
from ._callback import TokenUsageHandler
from .tools.event import LLMToolContext, resolve_tool_context
from .tools.bridge import get_agno_tools
from .tools.loader import build_agno_tools, resolve_agno_tool_specs

TOutput = TypeVar("TOutput")
OutputType = Literal["json_object"] | type[Any] | dict[str, Any]


class LLMService(Service):
    id = "miriata/llm"

    def __init__(self) -> None:
        super().__init__()
        self.total_tokens = 0
        self.total_calls = 0
        self.start_time: float = 0.0
        self.usage_handler = TokenUsageHandler(self)
        self._db: AsyncSqliteDb | None = None
        self._sessions: AgnoSessionStore | None = None
        self._memory_manager: MemoryManager | None = None
        self._agno_tool_specs = resolve_agno_tool_specs(_conf.agno_tools)

    @property
    def required(self) -> set[str]:
        return set()

    @property
    def stages(self) -> set[Phase]:
        return {"preparing", "blocking", "cleanup"}

    @property
    def session_store(self) -> AgnoSessionStore:
        if self._sessions is None:
            raise RuntimeError("Agno session store is not initialized")
        return self._sessions

    @property
    def memory_manager(self) -> MemoryManager:
        if self._memory_manager is None:
            raise RuntimeError("Agno memory manager is not initialized")
        return self._memory_manager

    @overload
    async def generate(
        self,
        message: str | list[Message],
        variables: dict[str, Any] | None = None,
        *,
        session: UserSession | None = None,
        stream: bool = False,
        system: str | None = None,
        model: str | None = None,
        output: type[TOutput],
        ignore_user_prompt: bool = False,
        **kwargs: Any,
    ) -> GenericResponse[TOutput]: ...

    @overload
    async def generate(
        self,
        message: str | list[Message],
        variables: dict[str, Any] | None = None,
        *,
        session: UserSession | None = None,
        stream: bool = False,
        system: str | None = None,
        model: str | None = None,
        output: Literal["json_object"] | dict[str, Any],
        ignore_user_prompt: bool = False,
        **kwargs: Any,
    ) -> GenericResponse[Any]: ...

    @overload
    async def generate(
        self,
        message: str | list[Message],
        variables: dict[str, Any] | None = None,
        *,
        session: UserSession | None = None,
        stream: bool = False,
        system: str | None = None,
        model: str | None = None,
        output: None = None,
        ignore_user_prompt: bool = False,
        **kwargs: Any,
    ) -> GenericResponse[None]: ...

    async def generate(
        self,
        message: str | list[Message],
        variables: dict[str, Any] | None = None,
        *,
        session: UserSession | None = None,
        stream: bool = False,
        system: str | None = None,
        model: str | None = None,
        output: OutputType | None = None,
        ignore_user_prompt: bool = False,
        **kwargs: Any,
    ) -> GenericResponse[Any]:
        """Generate an LLM response with optional user-scoped memory."""
        user_id = session.user_id if session is not None else None
        memory_enabled = (
            await memory_settings.is_enabled(user_id) if user_id is not None else False
        )
        return await self._run_agent(
            message,
            variables,
            tool_context=None,
            stream=stream,
            system=system,
            model=model,
            output=output,
            session_info=None,
            user_id=user_id,
            memory_enabled=memory_enabled,
            ignore_user_prompt=ignore_user_prompt,
            request_params=kwargs,
        )

    async def _generate_for_session(
        self,
        message: str | list[Message],
        variables: dict[str, Any] | None = None,
        *,
        session: SessionInfo,
        model: str | None = None,
        memory_enabled: bool = False,
        tool_context: LLMToolContext | None = None,
    ) -> GenericResponse[None]:
        """Generate a persisted response for Entari's chat session manager."""
        return await self._run_agent(
            message,
            variables,
            tool_context=tool_context,
            stream=False,
            system=None,
            model=model,
            output=None,
            session_info=session,
            user_id=session.user_id,
            memory_enabled=memory_enabled,
            ignore_user_prompt=False,
            request_params={},
        )

    async def _run_agent(
        self,
        message: str | list[Message],
        variables: dict[str, Any] | None,
        *,
        tool_context: LLMToolContext | None,
        stream: bool,
        system: str | None,
        model: str | None,
        output: OutputType | None,
        session_info: SessionInfo | None,
        user_id: int | str | None,
        memory_enabled: bool,
        ignore_user_prompt: bool,
        request_params: dict[str, Any],
    ) -> GenericResponse[Any]:
        output_schema, output_adapter = prepare_output_schema(output)
        if output_schema is not None and stream:
            raise ValueError("output is not supported when stream=True")

        model_config = get_model_config(model)
        if system is not None:
            selected_prompt = system
        elif ignore_user_prompt:
            selected_prompt = None
        else:
            selected_prompt = model_config.prompt or _conf.prompt or None

        instructions = (
            "\n\n".join(prompt for prompt in (_conf.system, selected_prompt) if prompt)
            or None
        )

        if variables:
            variable_instructions = "下列是用以辅助你思考回答的变量：\n" + "\n".join(
                f"- **{key}**: {value!r}" for key, value in variables.items()
            )
            instructions = (
                f"{instructions}\n\n{variable_instructions}"
                if instructions
                else variable_instructions
            )

        model_request_params = {**model_config.extra, **request_params}
        agno_model = LiteLLM(
            id=model_config.name,
            api_key=model_config.api_key,
            api_base=model_config.base_url,
            request_params=model_request_params or None,
        )

        resolved_tool_context = resolve_tool_context(tool_context, variables)

        agent_kwargs: dict[str, Any] = {
            "id": self.id,
            "model": agno_model,
            "instructions": instructions,
            "tools": [
                *get_agno_tools(resolved_tool_context),
                *build_agno_tools(self._agno_tool_specs),
            ],
            "tool_call_limit": _conf.tool_call_limit,
            "markdown": False,
            "store_media": False,
        }

        if output_schema is not None:
            agent_kwargs["output_schema"] = output_schema
            agent_kwargs["use_json_mode"] = True

        resolved_user_id = session_info.user_id if session_info is not None else user_id
        if resolved_user_id is not None:
            agent_kwargs["user_id"] = str(resolved_user_id)
            agent_kwargs["update_memory_on_run"] = memory_enabled
            agent_kwargs["enable_agentic_memory"] = memory_enabled
            agent_kwargs["add_memories_to_context"] = memory_enabled

            if memory_enabled and self._db is not None:
                agent_kwargs["db"] = self._db
                agent_kwargs["memory_manager"] = MemoryManager(
                    model=agno_model,
                    db=self._db,
                )

        if session_info is not None:
            if self._db is not None:
                agent_kwargs["db"] = self._db
            agent_kwargs["session_id"] = session_info.session_id
            agent_kwargs["add_history_to_context"] = True
            agent_kwargs["enable_session_summaries"] = True
            agent_kwargs["add_session_summary_to_context"] = False

        agent = Agent(**agent_kwargs)
        model_input = await inject_context_messages(message, resolved_tool_context)
        if stream:
            return GenericResponse.from_stream(
                agent.arun(model_input, stream=True, yield_run_output=True),
                on_finish=self.usage_handler.record,
            )

        result = await agent.arun(model_input)
        if result.status is RunStatus.error:
            raise RuntimeError(str(result.content or "Agno agent run failed"))

        self.usage_handler.record(result)

        return GenericResponse.from_run_output(
            result,
            structured=output_schema is not None,
            output_adapter=output_adapter,
        )

    async def get_user_memories(self, user_id: int | str) -> list[UserMemory]:
        memories = await self.memory_manager.aget_user_memories(user_id=str(user_id))
        return memories or []

    async def clear_user_memories(self, user_id: int | str) -> None:
        await self.memory_manager.aclear_user_memories(user_id=str(user_id))

    async def vision(
        self,
        image_url: str | dict[str, Any],
        system: str | None = None,
        model: str | None = None,
    ) -> GenericResponse[None]:
        """Describe an image through the standard generate path."""
        model_config = get_model_config(model)
        if not litellm.supports_vision(model_config.name):
            raise RuntimeError(
                f"Model {model_config.name} does not support vision input"
            )

        if isinstance(image_url, str):
            url = image_url
        else:
            image = image_url.get("image_url", image_url)
            url = image["url"] if isinstance(image, dict) else str(image)
        message = Message(
            role="user",
            content=[
                {"type": "text", "text": "Describe this image."},
                {"type": "image_url", "image_url": {"url": url}},
            ],
        )
        return await self.generate([message], system=system, model=model_config.name)

    async def launch(self, manager: Launart) -> None:
        async with self.stage("preparing"):
            litellm.drop_params = True
            self.start_time = time.time()
            db_path = local_data.get_data_file("llm", "agno.db")
            self._db = AsyncSqliteDb(db_file=str(db_path))
            self._sessions = AgnoSessionStore(self._db, self.id)
            self._memory_manager = MemoryManager(db=self._db)

        async with self.stage("blocking"):
            await manager.status.wait_for_sigexit()

        async with self.stage("cleanup"):
            if self._db is not None:
                await self._db.db_engine.dispose()
            self._memory_manager = None


llm = LLMService()
add_service(llm)
