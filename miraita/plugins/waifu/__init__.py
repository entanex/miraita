import random

from arclet.alconna import Alconna, CommandMeta
from arclet.entari import metadata, command, Session, At, Image, MessageChain

from .config import Config, config
from .data_source import get_waifu_data, save_waifu_data

metadata(
    name="娶群友",
    author=[{"name": "Komorebi", "email": "mute231010@gmail.com"}],
    description="随机抽取群友做老婆",
    classifier=["娱乐"],
    config=Config,
)

waifu_alc = Alconna(
    "waifu",
    meta=CommandMeta(
        description="随机抽取群友做老婆",
        usage="/waifu",
        example="/waifu",
    ),
)
waifu_disp = command.mount(waifu_alc)


@waifu_disp.handle()
async def _(session: Session):
    if not session.event.guild:
        await session.send("娶群友只允许在群聊中使用")
        return

    if await get_waifu_data(session.user.id):
        await session.send("已经有老婆了，不能花心")
        return

    members = (await session.guild_member_list()).data

    member = random.choice(members)

    if member.user is None or member.user.avatar is None:
        return

    if (
        random.random() < config.no_waifu_prob
        or member.user.is_bot
        or member.user.id == session.user.id
    ):
        return random.choice(config.no_waifu_text)

    msg = MessageChain(
        [
            Image(src=member.user.avatar),
            "你今天的群老婆是",
            At(member.user.id, name=member.user.name),
        ]
    )

    await save_waifu_data(session.user.id, member.user.id)

    await session.send(msg)
