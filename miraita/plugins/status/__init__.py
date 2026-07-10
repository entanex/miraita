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


status_alc = Alconna(
    "status",
    meta=CommandMeta(
        description="查看服务器状态",
        usage="/status",
        example="/status",
    ),
    namespace=ns,
)
status_disp = command.mount(status_alc).as_execute()


@status_disp.handle()
async def status(session: Session):
    await session.send([Image.of(raw=draw(), mime="image/png")])
