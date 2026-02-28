import json
from collections.abc import Sequence
from typing import Any, overload
from uuid import uuid4

import litellm
from arclet.letoderea import ExitState
from arclet.letoderea.typing import Contexts, generate_contexts
from entari_plugin_user import User, UserSession
from entari_plugin_database import get_session as get_db_session
from sqlalchemy import desc, func, select

from miraita.providers.llm._types import Message
from miraita.providers.llm.events.tools import LLMToolEvent, available_functions
from miraita.providers.llm.log import logger
from miraita.providers.llm.model import LLMSession, SessionContext
from miraita.providers.llm.service import llm


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
    async def _add_token_usage(cls, session_id: str, tokens: int) -> None:
        if tokens <= 0:
            return

        async with get_db_session() as db_session:
            user_session = await db_session.get(LLMSession, session_id)
            if user_session is None:
                return
            user_session.total_tokens += tokens
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
        user_input: str,
        ctx: Contexts,
        session: UserSession,
        model: str | None = None,
        new: bool = False,
    ) -> str:
        llm_session = await cls._get_active_session(session.user_id)
        if new or llm_session is None:
            llm_session = await cls._create_session(
                user_id=session.user_id, user_input=user_input, model=model
            )

        if llm_session.topic == "新对话":
            await cls._refresh_topic(llm_session, user_input=user_input, model=model)

        user_message: Message = {
            "role": "user",
            "content": user_input,
            "name": session.user.name,
        }
        await cls._persist_message(llm_session.session_id, user_message)

        messages = await cls._load_messages(llm_session.session_id)
        final_answer = ""
        for _ in range(8):
            response = await llm.generate(
                messages,
                stream=False,
                model=model,
                user=session.user.name,
            )

            usage = response.get("usage") or {}
            await cls._add_token_usage(
                llm_session.session_id,
                int(usage.get("total_tokens", 0) or 0),
            )

            response_message = response["choices"][0]["message"]
            tool_calls = response_message.tool_calls

            assistant_message: Message = {
                "role": "assistant",
                "content": response_message.content,
                "tool_calls": [tc.model_dump() for tc in tool_calls]
                if tool_calls
                else None,
            }
            messages.append(assistant_message)
            await cls._persist_message(llm_session.session_id, assistant_message)

            if tool_calls:
                calls = [
                    tc
                    for tc in tool_calls
                    if isinstance(tc, litellm.ChatCompletionMessageToolCall)
                ]
                for tool_call in calls:
                    function_name = tool_call.function.name
                    if function_name is None:
                        continue

                    function_to_call = available_functions[function_name]
                    function_args = json.loads(tool_call.function.arguments)
                    ctx1 = await generate_contexts(LLMToolEvent(), inherit_ctx=ctx)
                    logger.debug(
                        f"Calling tool: {function_name} with args: {function_args}"
                    )
                    try:
                        resp = await function_to_call.handle(
                            ctx1 | function_args, inner=True
                        )
                        if isinstance(resp, ExitState):
                            if resp.args[0] is not None:
                                result = {"ok": True, "data": resp.args[0]}
                            else:
                                result = {"ok": False, "error": "No response"}
                        else:
                            result = {"ok": True, "data": resp}
                    except Exception as e:
                        result = {"ok": False, "error": repr(e)}

                    tool_message: Message = {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "content": json.dumps(result, ensure_ascii=False),
                    }
                    messages.append(tool_message)
                    await cls._persist_message(llm_session.session_id, tool_message)
                continue

            final_answer = response_message.content or ""
            break

        if not final_answer:
            return "对话失败，请稍后再试"
        return final_answer
