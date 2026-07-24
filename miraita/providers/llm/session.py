from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from agno.db.base import SessionType
from agno.db.sqlite import AsyncSqliteDb
from agno.session.agent import AgentSession

from ._jsondata import (
    clear_current_session,
    clear_session_model,
    get_current_session,
    get_session_model,
    set_current_session,
    set_session_model,
)
from .stats import (
    MessageStats,
    TokenStats,
    collect_message_stats,
    collect_session_usage,
)


@dataclass(frozen=True, slots=True)
class SessionInfo:
    session_id: str
    user_id: str
    topic: str
    model: str
    is_active: bool
    messages: MessageStats
    tokens: TokenStats
    cost_usd: float
    created_at: datetime
    summary: str | None = None


class AgnoSessionStore:
    """Entari session selection backed by Agno conversation sessions."""

    def __init__(self, db: AsyncSqliteDb, agent_id: str) -> None:
        self.db = db
        self.agent_id = agent_id

    async def create(self, user_id: int | str, model: str) -> SessionInfo:
        user_id = str(user_id)
        created_at = int(time.time())
        session_id = uuid4().hex
        set_current_session(user_id, session_id, created_at)
        set_session_model(session_id, model)
        return self._pending_info(user_id, session_id, created_at, model)

    async def current(self, user_id: int | str) -> SessionInfo | None:
        user_id = str(user_id)
        pointer = get_current_session(user_id)
        if pointer is not None:
            return await self.get(user_id, pointer.session_id)

        sessions = await self._get_user_sessions(user_id)
        if not sessions:
            return None
        session = sessions[0]
        set_current_session(
            user_id,
            session.session_id,
            session.created_at or int(time.time()),
        )
        return self._to_info(session, session.session_id)

    async def get(
        self,
        user_id: int | str,
        session_id: str,
    ) -> SessionInfo | None:
        user_id = str(user_id)
        pointer = get_current_session(user_id)
        current_id = pointer.session_id if pointer is not None else None
        session = await self.db.get_session(
            session_id,
            SessionType.AGENT,
            user_id=user_id,
        )
        if isinstance(session, AgentSession):
            return self._to_info(session, current_id)
        if pointer is not None and pointer.session_id == session_id:
            return self._pending_info(
                user_id,
                session_id,
                pointer.created_at,
                get_session_model(session_id) or "",
            )
        return None

    async def list(self, user_id: int | str) -> list[SessionInfo]:
        user_id = str(user_id)
        pointer = get_current_session(user_id)
        current_id = pointer.session_id if pointer is not None else None
        sessions = await self._get_user_sessions(user_id)
        result = [self._to_info(session, current_id) for session in sessions]
        if pointer is not None and all(
            session.session_id != pointer.session_id for session in sessions
        ):
            result.insert(
                0,
                self._pending_info(
                    user_id,
                    pointer.session_id,
                    pointer.created_at,
                    get_session_model(pointer.session_id) or "",
                ),
            )
        return result

    async def activate(self, user_id: int | str, session_id: str) -> bool:
        user_id = str(user_id)
        pointer = get_current_session(user_id)
        if pointer is not None and pointer.session_id == session_id:
            return True

        session = await self.db.get_session(
            session_id,
            SessionType.AGENT,
            user_id=user_id,
        )
        if not isinstance(session, AgentSession):
            return False
        set_current_session(
            user_id,
            session_id,
            session.created_at or int(time.time()),
        )
        return True

    async def set_model(self, user_id: int | str, model: str) -> bool:
        session = await self.current(user_id)
        if session is None:
            return False
        set_session_model(session.session_id, model)
        return True

    async def delete(self, user_id: int | str, session_id: str) -> bool:
        user_id = str(user_id)
        pointer = get_current_session(user_id)
        is_current = pointer is not None and pointer.session_id == session_id
        session = await self.db.get_session(
            session_id,
            SessionType.AGENT,
            user_id=user_id,
        )
        if not isinstance(session, AgentSession):
            if is_current:
                clear_current_session(user_id)
                clear_session_model(session_id)
                return True
            return False

        deleted = await self.db.delete_session(session_id, user_id=user_id)
        if deleted:
            clear_session_model(session_id)
            if is_current:
                clear_current_session(user_id)
        return deleted

    async def _get_user_sessions(self, user_id: str) -> list[AgentSession]:
        rows = await self.db.get_sessions(
            session_type=SessionType.AGENT,
            user_id=user_id,
            component_id=self.agent_id,
            sort_by="created_at",
            sort_order="desc",
        )
        if isinstance(rows, tuple):
            rows = rows[0]
        return [session for session in rows if isinstance(session, AgentSession)]

    def _to_info(self, session: AgentSession, current_id: str | None) -> SessionInfo:
        summary = session.summary
        summary_text = summary.summary.strip() if summary and summary.summary else None
        if summary and summary.topics:
            topic = summary.topics[0].strip()
        elif summary_text:
            topic = summary_text.splitlines()[0]
        else:
            topic = "新对话"
        topic = topic[:24] or "新对话"

        messages = collect_message_stats(session.get_messages())
        tokens, cost_usd = collect_session_usage(session)
        return SessionInfo(
            session_id=session.session_id,
            user_id=str(session.user_id or ""),
            topic=topic,
            model=get_session_model(session.session_id) or self._stored_model(session),
            is_active=session.session_id == current_id,
            messages=messages,
            tokens=tokens,
            cost_usd=cost_usd,
            created_at=datetime.fromtimestamp(session.created_at or 0),
            summary=summary_text,
        )

    @staticmethod
    def _stored_model(session: AgentSession) -> str:
        agent_data = session.agent_data
        if not isinstance(agent_data, dict):
            return ""
        model = agent_data.get("model")
        if isinstance(model, str):
            return model
        if isinstance(model, dict):
            for key in ("id", "name", "model"):
                value = model.get(key)
                if isinstance(value, str) and value:
                    return value
        return ""

    @staticmethod
    def _pending_info(
        user_id: str, session_id: str, created_at: int, model: str
    ) -> SessionInfo:
        return SessionInfo(
            session_id=session_id,
            user_id=user_id,
            topic="新对话",
            model=model,
            is_active=True,
            messages=MessageStats(),
            tokens=TokenStats(),
            cost_usd=0.0,
            created_at=datetime.fromtimestamp(created_at),
        )
