from arclet.alconna import Alconna, CommandMeta
from arclet.entari import metadata, command, Session, Image

from .drawer import draw

metadata(
    name="服务器状态",
    author=[{"name": "Komorebi", "email": "mute231010@gmail.com"}],
    description="查看服务器状态",
    classifier=["工具"],
)

status = Alconna(
    "status",
    meta=CommandMeta(
        description="查看服务器状态",
        usage="/status",
        example="/status",
    ),
)


@command.on(status)
async def _(session: Session):
    await session.send([Image.of(raw=draw(), mime="image/png")])
