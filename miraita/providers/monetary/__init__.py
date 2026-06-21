from arclet.entari import metadata

from .service import monetary as monetary

metadata(
    name="货币系统",
    author=[{"name": "Komorebi", "email": "mute231010@gmail.com"}],
    description="Miraita 货币系统",
    classifier=["服务"],
)

__all__ = [
    "monetary",
]
