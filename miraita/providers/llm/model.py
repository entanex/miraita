import json
from datetime import datetime
from typing import Literal, TypeAlias, cast

from entari_plugin_database import Base
from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ._types import Message

ROLE: TypeAlias = Literal["user", "assistant", "tool"]


class LLMSession(Base):
    __tablename__ = "llm_session"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    topic: Mapped[str] = mapped_column(String(24))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    total_tokens: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    contexts = relationship(
        "SessionContext", back_populates="session", cascade="all, delete-orphan"
    )


class SessionContext(Base):
    __tablename__ = "llm_context"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("llm_session.session_id"), index=True
    )

    role: Mapped[ROLE] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    reasoning_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)

    tool_calls: Mapped[list | None] = mapped_column(JSON, nullable=True)
    tool_call_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    session = relationship("LLMSession", back_populates="contexts")

    @property
    def message(self) -> Message:
        msg = {"role": self.role, "content": self.content}

        if self.role == "user":
            if self.name:
                msg["name"] = self.name

        elif self.role == "assistant":
            if self.reasoning_content:
                msg["reasoning_content"] = self.reasoning_content
            if self.tool_calls:
                msg["tool_calls"] = json.dumps(self.tool_calls)
            msg["content"] = self.content

        elif self.role == "tool" and self.tool_call_id:
            msg["tool_call_id"] = self.tool_call_id

        elif self.role == "system":
            if self.name:
                msg["name"] = self.name

        return cast(Message, msg)
