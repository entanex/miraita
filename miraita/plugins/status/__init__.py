from arclet.alconna import Alconna, CommandMeta, Namespace, config
from arclet.entari import metadata, command, Session, Image

from .drawer import draw

metadata(
    name="服务器状态",
    author=[{"name": "Komorebi", "email": "mute231010@gmail.com"}],
    description="查看服务器状态",
    classifier=["工具"],
)

ns = Namespace("服务器状态")
config.namespaces["服务器状态"] = ns


status = Alconna(
    "status",
    meta=CommandMeta(
        description="查看服务器状态",
        usage="/status",
        example="/status",
    ),
    namespace=ns,
)


@command.on(status)
async def _(session: Session):
    await session.send([Image.of(raw=draw(), mime="image/png")])
