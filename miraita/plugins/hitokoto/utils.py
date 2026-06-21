from dataclasses import dataclass
from arclet.entari import Entari

from .config import config


@dataclass
class Hitokoto:
    hitokoto: str
    from_: str
    from_who: str | None = None


async def get_hitokoto() -> Hitokoto:
    app = Entari.current()
    codes = config.get_type_codes()

    response = await app.http.get(
        "https://v1.hitokoto.cn/", params=[("c", code) for code in codes]
    )
    response.raise_for_status()

    data = await response.json()
    return Hitokoto(
        hitokoto=data["hitokoto"], from_=data["from"], from_who=data.get("from_who")
    )
