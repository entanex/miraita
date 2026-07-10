from datetime import datetime

from entari_plugin_database import Base
from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column


class Interval(Base):
    __tablename__ = "interval"

    id: Mapped[int] = mapped_column(primary_key=True)
    """用户 ID"""
    name: Mapped[str] = mapped_column(String(255), primary_key=True)
    """过滤器标识"""
    value: Mapped[float] = mapped_column(nullable=False)
    """间隔时间"""
    last_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    """上次执行时间"""


class Semaphore(Base):
    __tablename__ = "semaphore"

    id: Mapped[int] = mapped_column(primary_key=True)
    """用户 ID"""
    name: Mapped[str] = mapped_column(String(255), primary_key=True)
    """过滤器标识"""
    count: Mapped[int] = mapped_column(nullable=False)
    """最大调用数"""
    value: Mapped[int] = mapped_column(default=0, nullable=False)
    """当前占用数"""
