from dataclasses import asdict
from typing import Any

import litellm
from agno.models.message import Message
from arclet.entari import Image, MessageChain, Text
from arclet.letoderea import Contexts, waterfall
from entari_plugin_user import UserSession

from miraita.providers.llm.config import get_model_config
from miraita.providers.llm.event import LLMCollectVariableEvent
from miraita.providers.llm.service import llm
from miraita.providers.llm.session import SessionInfo


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
        content: list[dict[str, Any]] = []
        if user_prompt.has(Text):
            content.append({"type": "text", "text": user_prompt.extract_plain_text()})
        if user_prompt.has(Image) and litellm.supports_vision(selected_model):
            for image in user_prompt.include(Image):
                content.append({"type": "image_url", "image_url": {"url": image.src}})
        user_message = Message(
            role="user",
            content=content,
            name=f"{session.user.name}({session.user.id})",
        )

        collect_event = LLMCollectVariableEvent(
            session.internal, llm_session, user_prompt
        )
        variables: dict[str, Any] = {}
        async for result in waterfall(collect_event, inherit_ctx=ctx):
            variables.update(result.value)

        response = await llm._generate_for_session(
            [user_message],
            variables,
            session=llm_session,
            model=selected_model,
        )
        final_answer = response.content or ""
        if not final_answer:
            return "对话失败，请稍后再试"
        return str(final_answer)
