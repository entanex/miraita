from arclet.entari import metadata, command
from arclet.alconna import Alconna, CommandMeta
from entari_plugin_user import UserSession

from .config import Config
from .utils import get_hitokoto as get_hitokoto

metadata(
    name="一言",
    author=[{"name": "Komorebi", "email": "mute231010@gmail.com"}],
    description="总有一句话，能打动你的心",
    classifier=["生活"],
    config=Config,
)


hitokoto_alc = Alconna(
    "hitokoto",
    meta=CommandMeta(
        description="一言",
        usage="/一言",
        example="/一言",
    ),
)
hitokoto_alc.shortcut("一言", {"command": "hitokoto", "prefix": True})
hitokoto_disp = command.mount(hitokoto_alc).as_execute()


@hitokoto_disp.handle()
async def hitokoto(session: UserSession):
    hitokoto = await get_hitokoto()
    await session.send(
        f"今日一言：<i>{hitokoto.hitokoto}</i>\n"
        f"—— {hitokoto.from_}"
        f"{f'（{hitokoto.from_who}）' if hitokoto.from_who else ''}"
        f"<button type='input' text='/一言'>再来一条</button>"
    )
