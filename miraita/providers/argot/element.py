from datetime import timedelta
from typing import Any
from dataclasses import field, dataclass

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
            self.expired_at = int(expired_at.total_seconds())
        else:
            self.expired_at = expired_at

        super().__init__()
        self.__post_init__()


register_element(Argot)
