from arclet.letoderea import BLOCK, on
from arclet.entari import command, metadata, MessageCreatedEvent, filter_

from entari_plugin_user import UserSession

from .config import Config, config

metadata(
    name="At 指令",
    author=[{"name": "Komorebi", "email": "mute231010@gmail.com"}],
    description="在有人发送「@机器人」时触发特定指令",
    classifier=["工具"],
    config=Config,
)


@(on(MessageCreatedEvent, priority=1000).if_(filter_.public).if_(filter_.notice_me))
async def at_command(session: UserSession):
    try:
        elements = session.internal.elements
        await command.execute(f"{config.execute} {elements}", session=session.internal)
    except RuntimeError:
        await command.execute(config.execute, session=session.internal)

    return BLOCK
