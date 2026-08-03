from contextlib import AsyncExitStack
from dataclasses import asdict
from typing import Any

import litellm
from agno.media import Image as AgnoImage
from agno.models.message import Message
from arclet.entari import Image, MessageChain
from arclet.letoderea import Contexts, waterfall
from entari_plugin_user import UserSession

from miraita.providers.llm.config import get_model_config
from miraita.providers.llm.event import LLMCollectVariableEvent
from miraita.providers.llm.memory import UserMemory, memory_settings
from miraita.providers.llm.service import llm
from miraita.providers.llm.session import SessionInfo
from miraita.providers.llm.tools import LLMToolContext, snapshot_tool_dependencies
from miraita.providers.temp import temp


class LLMSessionManager:
    @classmethod
    async def create_new_session(
        cls,
        user_id: int | str,
        model: str | None = None,
    ) -> SessionInfo:
        selected_model = model or get_model_config().name
        return await llm.session_store.create(user_id, selected_model)

    @classmethod
    async def resume(cls, user_id: int | str, session_id: str) -> bool:
        return await llm.session_store.activate(user_id, session_id)

    @classmethod
    async def delete(cls, user_id: int | str, session_id: str) -> bool:
        return await llm.session_store.delete(user_id, session_id)

    @classmethod
    async def get_session_info(
        cls,
        user_id: int | str,
        session_id: str | None = None,
    ) -> dict[str, Any] | None:
        session = (
            await llm.session_store.get(user_id, session_id)
            if session_id is not None
            else await llm.session_store.current(user_id)
        )
        return asdict(session) if session is not None else None

    @classmethod
    async def select_model(cls, user_id: int | str, model: str) -> bool:
        return await llm.session_store.set_model(user_id, model)

    @classmethod
    async def list_sessions(cls, user_id: int | str) -> list[SessionInfo]:
        return await llm.session_store.list(user_id)

    @classmethod
    async def memory_enabled(cls, user_id: int) -> bool:
        return await memory_settings.is_enabled(user_id)

    @classmethod
    async def set_memory_enabled(cls, user_id: int, enabled: bool) -> None:
        await memory_settings.set_enabled(user_id, enabled)

    @classmethod
    async def get_memories(cls, user_id: int) -> list[UserMemory]:
        return await llm.get_user_memories(user_id)

    @classmethod
    async def reset_memories(cls, user_id: int) -> None:
        await llm.clear_user_memories(user_id)

    @classmethod
    async def chat(
        cls,
        user_prompt: MessageChain,
        *,
        session: UserSession,
        ctx: Contexts,
        model: str | None = None,
        new: bool = False,
    ) -> str:
        user_id = session.user_id
        memory_enabled = await cls.memory_enabled(user_id)
        llm_session = None if new else await llm.session_store.current(user_id)
        if llm_session is None:
            selected_model = (
                model or get_model_config(None, session.internal.channel.id).name
            )
            llm_session = await llm.session_store.create(user_id, selected_model)

        selected_model = (
            llm_session.model
            or model
            or get_model_config(None, session.channel.id).name
        )
        text = user_prompt.extract_plain_text()

        collect_event = LLMCollectVariableEvent(
            session.internal, llm_session, user_prompt
        )
        variables: dict[str, Any] = {}
        async for result in waterfall(collect_event, inherit_ctx=ctx):
            variables.update(result.value)
        variables["session"] = session
        variables["platform"] = session.internal.account.platform
        tool_dependencies = snapshot_tool_dependencies(ctx)

        async with AsyncExitStack() as stack:
            images: list[AgnoImage] = []
            if user_prompt.has(Image) and litellm.supports_vision(selected_model):
                for image in user_prompt.include(Image):
                    downloaded = await stack.enter_async_context(
                        temp.download(
                            image.src,
                            account=session.internal.account,
                        )
                    )
                    mime_type = (
                        downloaded.content_type
                        if downloaded.content_type
                        and downloaded.content_type.startswith("image/")
                        else None
                    )
                    images.append(
                        AgnoImage(
                            filepath=downloaded.path,
                            mime_type=mime_type,
                        )
                    )

            tool_context = LLMToolContext(
                user_message=user_prompt,
                dependencies=tool_dependencies,
            )
            user_message = Message(
                role="user",
                content=text,
                images=images or None,
                name=f"{session.user.name}({session.user.id})",
            )
            response = await llm._generate_for_session(
                [user_message],
                variables,
                session=llm_session,
                model=selected_model,
                memory_enabled=memory_enabled,
                tool_context=tool_context,
            )
        final_answer = response.content or ""
        if not final_answer:
            return "对话失败，请稍后再试"
        return str(final_answer)
