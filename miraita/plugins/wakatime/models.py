from entari_plugin_database import Base
from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column


class User(Base):
    __tablename__ = "wakatime"

    id: Mapped[int] = mapped_column(primary_key=True)
    access_token: Mapped[str] = mapped_column(Text)
