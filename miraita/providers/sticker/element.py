from typing import Any
from typing_extensions import override
from dataclasses import dataclass, field

from satori.element import Image, register_element

from miraita.configs import STICKER_DIR

from .utils import get_img_data


@dataclass(repr=False)
class Sticker(Image):
    """表情元素"""

    name: str = field(default="")
    src: str = field(init=False)

    __names__ = ("name", "title", "width", "height")

    def __init__(self, name: str, **kwargs):
        self.name = name
        super().__init__(src="", **kwargs)
        self.__post_init__(kwargs.get("extra"))

    def __post_init__(self, extra: dict[str, Any] | None):
        self.src = self.source
        self.title = self.name
        super().__post_init__(extra)

    @property
    @override
    def tag(self) -> str:
        return "sticker"

    @property
    def source(self):
        return f"{STICKER_DIR}/{self.name}.webp"

    def to_image(self):
        raw = get_img_data(self.source)

        return Image.of(
            raw=raw,
            mime="image/webp",
            name=self.name,
            cache=self.cache,
            timeout=self.timeout,
        )


register_element(Sticker)
