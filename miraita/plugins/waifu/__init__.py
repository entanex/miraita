import random

from arclet.alconna import Alconna, CommandMeta, Namespace, config as alc_config
from arclet.entari import metadata, command, scheduler, At, Image, MessageChain
from entari_plugin_user import UserSession

from .config import Config, config
from .data_source import clear_waifu_data, get_waifu_data, save_waifu_data

metadata(
    name="娶群友",
    author=[{"name": "Komorebi", "email": "mute231010@gmail.com"}],
    description="随机抽取群友做老婆",
    classifier=["娱乐"],
    config=Config,
)

ns = Namespace("娶群友")
alc_config.namespaces["娶群友"] = ns

waifu_alc = Alconna(
    "waifu",
    meta=CommandMeta(
        description="随机抽取群友做老婆",
        usage="/waifu",
        example="/waifu",
    ),
    namespace=ns,
)
waifu_disp = command.mount(waifu_alc)


@waifu_disp.handle()
async def _(session: UserSession):
    if not session.internal.event.guild:
        await session.send("娶群友只允许在群聊中使用")
        return

    if await get_waifu_data(str(session.user_id)):
        await session.send("已经有老婆了，不能花心")
        return

    members = (await session.internal.guild_member_list()).data

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

    await save_waifu_data(str(session.user_id), member.user.id)

    await session.send(msg)


@scheduler.cron("0 0 * * *")
async def refresh():
    await clear_waifu_data()
