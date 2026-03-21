import asyncio

from arclet.letoderea import BLOCK
from arclet.alconna import (
    Alconna,
    Args,
    CommandMeta,
    Subcommand,
    Namespace,
    config as alc_config,
)
from arclet.entari import At, ChannelType, Image, Session, command, metadata
from entari_plugin_database import AsyncSession
from entari_plugin_user import UserSession, get_user
from asyncio import TimeoutError
from miraita.providers.argot import Argot, on_argot
from miraita.utils.reaction import with_reaction

from .apis import API
from .log import logger
from .config import Config
from .exception import BindUserException, UserUnboundException
from .models import User
from .mount import build_authorize_url, create_state, is_mountable
from .render import render_wakatime
from .schemas import WakaTime
from .utils import get_background_image


metadata(
    name="谁是卷王",
    author=[{"name": "Komorebi", "email": "mute231010@gmail.com"}],
    description="将代码统计嵌入 Bot 中",
    classifier=["工具"],
    config=Config,
)

ns = Namespace("谁是卷王")
alc_config.namespaces["谁是卷王"] = ns

wakatime_alc = Alconna(
    "wakatime",
    Args["target?#目标", At | int],
    Subcommand("bind", Args["code?#授权码", str], help_text="绑定 WakaTime"),
    Subcommand("revoke", help_text="解绑 WakaTime"),
    meta=CommandMeta(
        description="查看 WakaTime 统计",
        usage="/wakatime [@某人]",
        example="/wakatime",
    ),
    namespace=ns,
)
wakatime_alc.shortcut("waka", {"command": "wakatime", "prefix": True})
wakatime_disp = command.mount(wakatime_alc)


@wakatime_disp.handle(priority=20)
@with_reaction
async def _(session: UserSession, target: command.Match[At | int]):
    target_name = "你"
    target_id = session.user_id
    if target.available:
        if isinstance(target.result, At) and target.result.id:
            pid = target.result.id
        else:
            pid = str(target.result)

        platform_user = await session.internal.user_get(pid)
        target_user = await get_user(session.platform, platform_user)
        target_id = target_user.id
        target_name = target_user.name

    try:
        (
            user_info,
            stats_info,
            stats_bar_info,
            all_time_since_today,
            background_image,
        ) = await asyncio.gather(
            API.get_user_info(target_id),
            API.get_user_stats(target_id),
            API.get_user_stats_bar(target_id),
            API.get_all_time_since_today(target_id),
            get_background_image(),
        )
    except UserUnboundException:
        await session.send(
            f"{target_name}还没有绑定 WakaTime 账号，"
            "请私聊我并使用 /wakatime bind 进行绑定"
        )
        return BLOCK
    except TimeoutError:
        await session.send("网络超时，再试试叭")
        return BLOCK
    except Exception:
        logger.exception("查询 WakaTime 数据失败")
        await session.send("查询失败，请稍后重试")
        return BLOCK

    result = WakaTime(
        user=user_info,
        stats=stats_info,
        stats_bar=stats_bar_info,
        all_time_since_today=all_time_since_today,
        background_image=background_image,
    )

    data = await render_wakatime(result)
    if isinstance(data, str):
        await session.send(data)
    else:
        await session.send(
            [
                Image.of(raw=data, mime="image/png"),
                Argot("wakatime", data={"background": background_image}),
            ]
        )
    return BLOCK


@wakatime_disp.assign("bind")
async def _(
    code: command.Match[str],
    session: UserSession,
    db_session: AsyncSession,
):
    if session.channel_type != ChannelType.DIRECT:
        await session.send("绑定指令只允许在私聊中使用")
        return BLOCK

    bound = await db_session.get(User, session.user_id)
    if bound is not None:
        await session.send("已绑定过 WakaTime 账号")
        return BLOCK

    if not code.available:
        state = create_state(session.user.id)
        auth_url = build_authorize_url(state)
        if is_mountable():
            await session.send(f"前往该页面绑定 WakaTime 账号：{auth_url}\n")
        else:
            await session.send(
                f"前往该页面绑定 WakaTime 账号：{auth_url}\n"
                "完成后请使用 /wakatime bind <code> 提交授权码。"
            )
        return BLOCK

    try:
        access_token = await API.bind_user(code.result)

        db_session.add(User(id=session.user.id, access_token=access_token))
        await db_session.commit()

        await session.send("绑定成功")
    except BindUserException:
        logger.exception(f"用户 {session.user.id} 绑定失败")
        await session.send("绑定失败，请检查 code 是否正确")
    return BLOCK


@wakatime_disp.assign("revoke")
async def _(session: UserSession, db_session: AsyncSession):
    user = await db_session.get(User, session.user_id)
    if user is None:
        await session.send("你还没有绑定 WakaTime 账号")
        return BLOCK

    try:
        status_code = await API.revoke_user_token(session.user_id)
        if status_code != 200:
            logger.error(f"用户 {session.user.id} 解绑失败。状态码：{status_code}")
            await session.send("解绑失败")
            return BLOCK

        user = await db_session.get(User, session.user.id)
        if user is not None:
            await db_session.delete(user)
            await db_session.commit()
        await session.send("已解绑")
    except Exception:
        logger.exception(f"用户 {session.user.id} 解绑失败")
        await session.send("解绑失败")
    return BLOCK


@on_argot("background")
async def _(session: Session, argot: Argot):
    if background := argot.data.get("background"):
        if isinstance(background, str):
            await session.send([Image.of(url=background)])
        else:
            await session.send([Image.of(path=background)])
