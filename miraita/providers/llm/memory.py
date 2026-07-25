from agno.db.schemas.memory import UserMemory as UserMemory

from entari_plugin_database import Base
from entari_plugin_database import get_session as get_db_session
from sqlalchemy import Boolean
from sqlalchemy.orm import Mapped, mapped_column


class LLMMemorySetting(Base):
    __tablename__ = "llm_memory_setting"

    user_id: Mapped[int] = mapped_column(primary_key=True)
    """用户 ID"""
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    """是否启用"""


class MemorySettingStore:
    async def is_enabled(self, user_id: int) -> bool:
        async with get_db_session() as db_session:
            setting = await db_session.get(LLMMemorySetting, user_id)
            return setting.enabled if setting is not None else False

    async def set_enabled(self, user_id: int, enabled: bool) -> None:
        async with get_db_session() as db_session:
            setting = await db_session.get(LLMMemorySetting, user_id)
            if setting is None:
                db_session.add(LLMMemorySetting(user_id=user_id, enabled=enabled))
            else:
                setting.enabled = enabled
            await db_session.commit()


memory_settings = MemorySettingStore()
