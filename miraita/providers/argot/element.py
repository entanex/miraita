import time
from datetime import timedelta
from dataclasses import field, dataclass
from typing import Any

from satori.element import Element, register_element


@dataclass(init=False, repr=False)
class Argot(Element):
    """暗语消息元素"""

    name: str
    data: dict[str, Any]
    expired_at: int | None = field(default=None)

    def __init__(
        self,
        name: str,
        data: dict[str, Any],
        expired_at: int | timedelta | None = None,
    ):
        self.name = name
        self.data = data

        if isinstance(expired_at, timedelta):
            self.expired_at = int(time.time() + expired_at.total_seconds())
        else:
            self.expired_at = expired_at

        super().__init__()

    @classmethod
    def unpack(cls, attrs: dict[str, Any]):
        obj = cls(
            name=attrs["name"],
            data=attrs["data"],
            expired_at=attrs.get("expired_at"),
        )
        obj._attrs.update(attrs)
        return obj


register_element(Argot)
