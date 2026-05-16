from collections.abc import Sequence
from typing import Any, overload
from uuid import uuid4

import litellm
from arclet.entari import Image, MessageChain, Text
from arclet.letoderea.context import Contexts
from entari_plugin_user import User, UserSession
from entari_plugin_database import get_session as get_db_session
from sqlalchemy import desc, func, select

from miraita.providers.llm import llm, get_model_config
from miraita.providers.llm._types import Message
from miraita.providers.llm.model import LLMSession, SessionContext


class LLMSessionManager:
    @classmethod
    async def _generate_topic(cls, user_input: str, model: str | None = None) -> str:
        prompt = (
            "请根据用户的这句输入，生成一个简短的话题标题。"
            "只输出标题，不要解释，限制在12个字以内。\n"
            f"用户输入：{user_input}"
        )
        try:
            result = await llm.generate(prompt, stream=False, model=model)
            topic = (result.choices[0]["message"]["content"] or "").strip()
            return topic or "新对话"
        except Exception:
            return "新对话"

    @classmethod
    async def _get_active_session(cls, user_id: int) -> LLMSession | None:
        async with get_db_session() as db_session:
            stmt = (
                select(LLMSession)
                .where(LLMSession.user_id == user_id, LLMSession.is_active.is_(True))
                .order_by(desc(LLMSession.created_at))
                .limit(1)
            )
            return await db_session.scalar(stmt)

    @overload
    @classmethod
    async def _create_session(
        cls, user_id: int, *, topic: str, model: str | None = None
    ) -> LLMSession: ...

    @overload
    @classmethod
    async def _create_session(
        cls, user_id: int, *, user_input: str, model: str | None = None
    ) -> LLMSession: ...

    @classmethod
    async def _create_session(
        cls,
        user_id: int,
        user_input: str | None = None,
        topic: str | None = None,
        model: str | None = None,
    ) -> LLMSession:
        if topic is None and user_input:
            topic = await cls._generate_topic(user_input=user_input, model=model)

        user_session = LLMSession(
            session_id=uuid4().hex, user_id=user_id, topic=topic, is_active=True
        )
        async with get_db_session() as db_session:
            active_stmt = select(LLMSession).where(
                LLMSession.user_id == user_id, LLMSession.is_active.is_(True)
            )
            active_sessions = (await db_session.scalars(active_stmt)).all()
            for active in active_sessions:
                active.is_active = False
            db_session.add(user_session)
            await db_session.commit()
        return user_session

    @classmethod
    async def _load_messages(cls, session_id: str) -> list[Message]:
        async with get_db_session() as db_session:
            stmt = (
                select(SessionContext)
                .where(SessionContext.session_id == session_id)
                .order_by(SessionContext.id.asc())
            )
            contexts = list((await db_session.scalars(stmt)).all())
        return [context.message for context in contexts]

    @classmethod
    async def _build_user_message(
        cls,
        message: MessageChain,
        *,
        session: UserSession,
        model: str | None = None,
    ) -> Message:
        content = []
        model = model or get_model_config().name

        if message.has(Text):
            content.append({"type": "text", "text": message.extract_plain_text()})

        if message.has(Image) and litellm.supports_vision(model):
            img_chain = message.include(Image)
            for img in img_chain:
                content.append({"type": "image_url", "image_url": {"url": img.src}})

        user_message: Message = {
            "role": "user",
            "content": content,
            "name": session.user.name,
        }

        return user_message

    @classmethod
    async def _persist_message(cls, session_id: str, message: Message) -> None:
        async with get_db_session() as db_session:
            db_session.add(
                SessionContext(
                    session_id=session_id,
                    role=message["role"],
                    content=message["content"],
                    reasoning_content=message.get("reasoning_content"),
                    name=message.get("name"),
                    tool_calls=message.get("tool_calls"),
                    tool_call_id=message.get("tool_call_id"),
                )
            )
            await db_session.commit()

    @classmethod
    async def _refresh_topic(
        cls,
        llm_session: LLMSession,
        user_input: str,
        model: str | None = None,
    ) -> None:
        async with get_db_session() as db_session:
            user_session = await db_session.get(LLMSession, llm_session.session_id)
            if user_session is None:
                return
            user_session.topic = await cls._generate_topic(
                user_input=user_input, model=model
            )
            await db_session.commit()
            llm_session.topic = user_session.topic

    @classmethod
    async def create_new_session(cls, user: User) -> LLMSession:
        return await cls._create_session(user_id=user.id, topic="新对话")

    @classmethod
    async def switch(cls, user: User, session_id: str) -> bool:
        async with get_db_session() as db_session:
            target = await db_session.get(LLMSession, session_id)
            if target is None or target.user_id != user.id:
                return False

            if target.is_active:
                return True

            active_stmt = select(LLMSession).where(
                LLMSession.user_id == user.id, LLMSession.is_active.is_(True)
            )
            active_sessions = (await db_session.scalars(active_stmt)).all()
            for active in active_sessions:
                active.is_active = False
            target.is_active = True
            await db_session.commit()
            return True

    @classmethod
    async def delete(cls, user: User, session_id: str) -> bool:
        async with get_db_session() as db_session:
            user_session = await db_session.get(LLMSession, session_id)
            if user_session is None or user_session.user_id != user.id:
                return False
            await db_session.delete(user_session)
            await db_session.commit()
            return True

    @classmethod
    async def get_current_session_info(cls, user: User) -> dict[str, Any] | None:
        async with get_db_session() as db_session:
            stmt = (
                select(LLMSession)
                .where(LLMSession.user_id == user.id, LLMSession.is_active.is_(True))
                .order_by(desc(LLMSession.created_at))
                .limit(1)
            )
            session = await db_session.scalar(stmt)
            if session is None:
                return None

            count_stmt = (
                select(func.count(SessionContext.id))
                .where(SessionContext.session_id == session.session_id)
                .where(SessionContext.role.in_(("user", "assistant")))
            )
            message_count = int(await db_session.scalar(count_stmt) or 0)

            return {
                "session_id": session.session_id,
                "topic": session.topic,
                "is_active": session.is_active,
                "created_at": session.created_at,
                "message_count": message_count,
                "total_tokens": session.total_tokens,
            }

    @classmethod
    async def list_sessions(cls, user: User) -> Sequence[LLMSession]:
        async with get_db_session() as db_session:
            stmt = (
                select(LLMSession)
                .where(LLMSession.user_id == user.id)
                .order_by(desc(LLMSession.created_at))
            )
            return list((await db_session.scalars(stmt)).all())

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
        user_message = await cls._build_user_message(
            user_prompt, session=session, model=model
        )
        llm_session = await cls._get_active_session(session.user_id)
        if new or llm_session is None:
            llm_session = await cls._create_session(
                user_id=session.user_id,
                user_input=user_prompt.extract_plain_text(),
                model=model,
            )

        if llm_session.topic == "新对话":
            await cls._refresh_topic(
                llm_session, user_input=user_prompt.extract_plain_text(), model=model
            )

        await cls._persist_message(llm_session.session_id, user_message)

        messages = await cls._load_messages(llm_session.session_id)

        async def on_message_callback(message: Message) -> None:
            await cls._persist_message(llm_session.session_id, message)

        response = await llm.generate(
            messages,
            stream=False,
            model=model,
            user=session.user.name,
            on_message=on_message_callback,
        )

        response_message = response.choices[0].message
        final_answer = response_message.content or ""
        if not final_answer:
            return "对话失败，请稍后再试"
        return final_answer
