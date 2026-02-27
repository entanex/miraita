from entari_plugin_database import Base
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column


class User(Base):
    __tablename__ = "wakatime"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    access_token: Mapped[str] = mapped_column(Text)
