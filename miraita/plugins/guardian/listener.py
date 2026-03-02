from contextlib import suppress
from json import JSONDecodeError

from arclet.entari import plugin, At, Text, Image, Session, MessageChain
from arclet.entari.event.base import (
    GuildMemberAddedEvent,
    GuildMemberRemovedEvent,
    GuildMemberRequestEvent,
    ReactionAddedEvent,
)
from entari_plugin_user import UserSession

from miraita.providers.argot import Argot, on_argot, on_reaction

from . import filter
from .utils import check_member_permission


@plugin.listen(GuildMemberAddedEvent)
@filter.is_subscribed
async def guild_member_added(session: Session[GuildMemberAddedEvent]):
    guild_id = session.event.guild.id
    user_id = session.event.user.id

    guild = await session.account.guild_get(guild_id)
    user = await session.account.user_get(user_id)

    welcome_message = MessageChain(
        [
            "👋 欢迎 ",
            At(user.id, name=user.name),
            f" 加入 {guild.name} !\n",
        ]
    )

    if operator := session.event.operator:
        operator = await session.account.user_get(operator.id)
        welcome_message.append(Text(f"处理人：{operator.name}"))

    await session.send(welcome_message)


@plugin.listen(GuildMemberRemovedEvent)
@filter.is_subscribed
async def guild_member_removed(session: Session[GuildMemberRemovedEvent]):
    user_id = session.event.user.id
    user = await session.account.user_get(user_id)

    await session.send(f"{user.name}({user_id}) 退群了")


@plugin.listen(GuildMemberRequestEvent)
@filter.is_subscribed
async def guild_member_request(session: Session[GuildMemberRequestEvent]):
    guild_id = session.event.guild.id
    user_id = session.event.user.id
    message = session.event.message

    user = await session.account.user_get(user_id)

    receipt = MessageChain(
        [
            f"收到新的入群请求：{user.name}({user.id})\n",
            f"> {message.content}\n" if message.content else "",
            Image(src=user.avatar) if user.avatar else "",
            "> Tip: 回复 `/approve` 或 `/refuse` 以处理",
            Argot(
                name=f"guild-member-requested-{guild_id}-{user_id}",
                data={"message_id": message.id},
            ),
        ]
    )
    await session.send(receipt)


@on_argot("approve")
@on_reaction(["124", "424"])
async def _(argot: Argot, session: UserSession):
    if isinstance(session.internal.event, ReactionAddedEvent):
        member = await session.internal.guild_member_get(session.platform_id)
    else:
        member = session.internal.member

    if not check_member_permission(member) or session.user.authority <= 3:
        await session.send("权限不足")
        return

    message_id = argot.data.get("message_id")
    if message_id is None:
        return

    await session.internal.account.guild_member_approve(message_id, True, "")


@on_argot("refuse [comment:str]")
@on_reaction(["123"])
async def _(argot: Argot, session: UserSession, comment: str = ""):
    if isinstance(session.internal.event, ReactionAddedEvent):
        member = await session.internal.guild_member_get(session.platform_id)
    else:
        member = session.internal.member

    if not check_member_permission(member) or session.user.authority <= 3:
        await session.send("权限不足")
        return

    message_id = argot.data.get("message_id")
    if message_id is None:
        return

    with suppress(JSONDecodeError):
        await session.internal.account.guild_member_approve(message_id, False, comment)
