from entari_plugin_database import Base
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column


class Monetary(Base):
    __tablename__ = "monetary"

    id: Mapped[int] = mapped_column(primary_key=True)
    """用户 ID"""
    currency: Mapped[str] = mapped_column(String(64), primary_key=True)
    """货币"""
    value: Mapped[int] = mapped_column(default=0, nullable=False)
    """货币数值"""
