from contextlib import suppress
from satori.exception import ActionFailed
from arclet.entari import (
    metadata,
    command,
    At,
    Session,
    MessageCreatedEvent,
    ChannelType,
)
from arclet.alconna import Args, MultiVar, Option, Alconna, CommandMeta, store_true

from .utils import resolve_events
from . import listener as listener

from miraita.providers.datastore import datastore


metadata(
    name="群管",
    author=[{"name": "Komorebi", "email": "mute231010@gmail.com"}],
    description="群聊管理",
    classifier=["工具"],
)


mute = Alconna(
    "mute",
    Args["target#目标", At | int]["duration?#时长(min)", int, 5],
    meta=CommandMeta(
        description="禁言群成员",
        usage="/mute @成员 [时长(min)]",
        example="/mute @Komorebi 10",
    ),
)


kick = Alconna(
    "kick",
    Args["target#目标", At | int],
    Option("-p|--permanent", action=store_true, help_text="是否永久踢出"),
    meta=CommandMeta(
        description="踢出群成员",
        usage="/kick @成员 [-p|--permanent]",
        example="/kick @Komorebi",
    ),
)

withdraw = Alconna(
    "withdraw",
    meta=CommandMeta(
        description="撤回消息",
        usage="回复指定消息",
    ),
)
withdraw.shortcut("recall", {"command": "withdraw", "prefix": True})
withdraw.shortcut("撤回", {"command": "withdraw", "prefix": True})

guard = Alconna(
    "guard",
    Args["events?#事件", MultiVar(str)],
    Option("-r|--revoke", action=store_true, help_text="取消订阅"),
    meta=CommandMeta(
        description="订阅群组事件",
        usage="/guard guild-member-added guild-member-removed",
        example="/guard all",
    ),
)


@command.on(mute)
async def _(session: Session, target: At | int, duration: int = 5):
    if not session.event.guild:
        await session.send("该操作只允许在群聊中使用")
        return

    if isinstance(target, At) and target.id:
        target_id = target.id
        target_name = target.name
    elif isinstance(target, int):
        target_id = str(target)
        target_name = (await session.guild_member_get(target_id)).nick
    else:
        await session.send("无效的目标成员")
        return

    with suppress(ActionFailed):
        await session.guild_member_mute(target_id, duration * 60)
        await session.send(f"已禁言 {target_name} {duration} 秒")


@command.on(kick)
async def _(
    session: Session,
    target: At | int,
    permanent: command.Query[bool] = command.Query("permanent.value"),
):
    if not session.event.guild:
        await session.send("该操作只允许在群聊中使用")
        return

    if isinstance(target, At) and target.id:
        target_id = target.id
        target_name = target.name
    elif isinstance(target, int):
        target_id = str(target)
        target_name = (await session.guild_member_get(target_id)).nick
    else:
        await session.send("无效的目标成员")
        return

    with suppress(ActionFailed):
        await session.guild_member_kick(target_id, permanent.available)
        await session.send(f"已将 {target_name} 踢出群聊")


@command.on(withdraw)
async def _(session: Session[MessageCreatedEvent]):
    if session.event.quote is None or session.event.quote.id is None:
        await session.send("需回复要撤回的消息")
        return

    with suppress(ActionFailed):
        await session.account.message_delete(session.channel.id, session.event.quote.id)


@command.on(guard)
async def _(
    session: Session,
    events: command.Match[tuple[str, ...]],
    revoke: command.Query[bool] = command.Query("revoke.value"),
):
    channel_id = session.channel.id

    if session.channel.type == ChannelType.DIRECT:
        await session.send("仅支持群组事件订阅")
        return

    if not events.available:
        await session.send("请提供要操作的事件，例如 /subscribe guild-member-added")
        return

    resolved, invalid = resolve_events(events.result)
    current = set(datastore.get(channel_id, []))

    if revoke.available:
        current.difference_update(resolved)
    else:
        current.update(resolved)

    datastore.set(channel_id, sorted(current))

    lines: list[str] = []

    if invalid:
        lines.append(f"无效事件: {', '.join(sorted(invalid))}")

    if revoke.available:
        lines.append(f"已取消事件 {', '.join(sorted(resolved))} 订阅")
    else:
        lines.append(f"已订阅: {', '.join(sorted(resolved))}")

    lines.append("当前订阅: " + (", ".join(sorted(current)) if current else "无"))
    await session.send("\n".join(lines))
