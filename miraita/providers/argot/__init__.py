from arclet.entari import metadata
from arclet.entari.core import global_providers

from . import listener as listener
from .element import Argot as Argot
from .command import on_argot as on_argot
from .provider import ArgotProvider as ArgotProvider

metadata(
    name="暗语消息",
    author=["Komorebi <mute231010@gmail.com>"],
    description="暗语消息",
    classifier=["服务"],
)


global_providers.extend([ArgotProvider()])
