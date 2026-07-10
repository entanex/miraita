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
        self._extra = kwargs.get("extra")
        super().__init__(src="", **kwargs)
        self.__post_init__()

    def __post_init__(self):
        self.src = self.source
        self.title = self.name

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
