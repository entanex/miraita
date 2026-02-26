from arclet.entari import metadata

from . import listener as listener
from .element import Sticker as Sticker

metadata(
    name="表情包",
    author=["Komorebi <mute231010@gmail.com>"],
    description="为 miraita 消息提供表情包支持",
    classifier=["服务"],
)


__all__ = ["Sticker"]
