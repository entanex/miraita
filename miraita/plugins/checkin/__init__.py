import random
from datetime import datetime, timedelta

from arclet.entari import metadata, command
from arclet.alconna import Alconna, CommandMeta

from entari_plugin_user import UserSession

from miraita.utils.cooldown import interval
from miraita.providers.monetary import monetary
from miraita.plugins.hitokoto import get_hitokoto

from .config import config, Config

metadata(
    name="签到",
    author=[{"name": "Komorebi", "email": "mute231010@gmail.com"}],
    description="今天你打卡了没",
    classifier=["娱乐"],
    config=Config,
)

checkin_alc = Alconna(
    "checkin",
    meta=CommandMeta(
        description="签到",
        usage="/签到",
        example="/签到",
    ),
)
checkin_alc.shortcut("签到", {"command": "checkin", "prefix": True})
checkin_disp = command.mount(checkin_alc).as_execute()


@checkin_disp.handle()
@interval(
    (
        datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        + timedelta(days=1)
        - datetime.now()
    ).total_seconds(),
    "你今天已经签到过了！<sticker name='托腮' />",
)
async def checkin(session: UserSession):
    hitokoto = await get_hitokoto()

    coin = await monetary.gain(
        session.user_id,
        random.randint(*config.coin) if isinstance(config.coin, tuple) else config.coin,
        "coin",
    )

    exp = await monetary.gain(
        session.user_id,
        random.randint(*config.exp) if isinstance(config.exp, tuple) else config.exp,
        "exp",
    )

    favor = await monetary.gain(
        session.user_id,
        random.randint(*config.favor)
        if isinstance(config.favor, tuple)
        else config.favor,
        "favor",
    )

    await session.send(
        f"签到成功！\n"
        f"获得 <b>{coin}</b> 点金币，<b>{exp}</b> 点经验，<b>{favor}</b> 点好感度<br/>"
        f"<blockquote>今日一言：<i>{hitokoto.hitokoto}</i>\n"
        f"—— {hitokoto.from_}"
        f"{f'（{hitokoto.from_who}）' if hitokoto.from_who else ''}"
        f"</blockquote>"
    )
