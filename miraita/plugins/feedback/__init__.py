from asyncio import sleep

from arclet.alconna import (
    Args,
    Option,
    Alconna,
    MultiVar,
    Namespace,
    CommandMeta,
    store_true,
    config as alc_config,
)
from arclet.entari import Quote, Entari, Session, command, metadata, MessageCreatedEvent
from arclet.letoderea import BLOCK, on
from satori.client.account import Account
from satori.exception import ActionFailed, ServerException
from entari_plugin_user import UserSession

from .log import logger
from .config import Config, config
from .data_source import (
    Receiver,
    FeedbackData,
    get_feedback,
    save_feedback,
    load_receivers,
    save_receivers,
    delete_feedback,
)


metadata(
    name="反馈",
    author=[{"name": "Komorebi", "email": "mute231010@gmail.com"}],
    description="向开发者反馈信息，并支持从反馈频道直接回复",
    classifier=["工具"],
    config=Config,
)

ns = Namespace("反馈")
alc_config.namespaces["反馈"] = ns

feedback_alc = Alconna(
    "feedback",
    Args["message?#反馈内容", MultiVar(str)],
    Option("-r|--receive", action=store_true, help_text="添加到反馈频道列表"),
    Option(
        "-R|--no-receive",
        dest="unreceive",
        action=store_true,
        help_text="从反馈频道列表移除",
    ),
    meta=CommandMeta(
        description="发送反馈信息",
        usage="/feedback <message>",
        example="/feedback 希望增加一个新功能",
    ),
    namespace=ns,
)

feedback_disp = command.mount(feedback_alc)


def _receiver_key(receiver: Receiver) -> tuple[str, str, str, str | None]:
    return (
        receiver.platform,
        receiver.self_id,
        receiver.channel_id,
        receiver.guild_id,
    )


def _current_receiver(session: Session) -> Receiver:
    return Receiver(
        platform=session.account.platform,
        self_id=session.account.self_id,
        channel_id=session.channel.id,
        guild_id=session.event.guild.id if session.event.guild else None,
    )


def _find_account(platform: str, self_id: str) -> Account | None:
    for account in Entari.current().accounts.values():
        if account.platform == platform and account.self_id == self_id:
            return account
    return None


def _format_feedback_message(session: UserSession, text: str) -> str:
    platform_name = session.user_name or session.platform_id
    if platform_name == session.platform_id:
        nickname = session.platform_id
    else:
        nickname = f"{platform_name} ({session.platform_id})"
    return f"[feedback:{nickname}] {text}"


def _format_receiver_list(receivers: list[Receiver]) -> str:
    if not receivers:
        return "当前反馈频道：\n  - 无"

    lines = ["当前反馈频道："]
    for receiver in receivers:
        lines.append(
            f"  - {receiver.guild_id or ''}:{receiver.channel_id} ({receiver.platform})"
        )
    return "\n".join(lines)


async def _update_receiver(session: UserSession, receive: bool):
    if session.user.authority < 3:
        await session.send("权限不足")
        return BLOCK

    receivers = load_receivers()
    current = _current_receiver(session.internal)
    current_key = _receiver_key(current)
    index = next(
        (
            index
            for index, receiver in enumerate(receivers)
            if _receiver_key(receiver) == current_key
        ),
        -1,
    )

    if receive:
        if index >= 0:
            await session.send("当前频道已在反馈频道列表中")
            return BLOCK
        receivers.append(current)
        logger.info(
            "add feedback channel: "
            f"{current.guild_id}:{current.channel_id}({current.platform})"
        )
    else:
        if index < 0:
            await session.send("当前频道不在反馈频道列表中")
            return BLOCK
        removed = receivers.pop(index)
        logger.info(
            "remove feedback channel: "
            f"{removed.guild_id}:{removed.channel_id}({removed.platform})"
        )

    save_receivers(receivers)
    action = "添加" if receive else "删除"
    await session.send(f"反馈接收频道{action}成功\n{_format_receiver_list(receivers)}")
    return BLOCK


@feedback_disp.assign("receive")
async def _(session: UserSession):
    return await _update_receiver(session, True)


@feedback_disp.assign("unreceive")
async def _(session: UserSession):
    return await _update_receiver(session, False)


@feedback_disp.assign("$main")
async def _(session: UserSession, message: command.Match[tuple[str, ...]]):
    if not message.available:
        await session.send("请输入要反馈的内容")
        return BLOCK

    text = " ".join(message.result).strip()
    if not text:
        await session.send("请输入要反馈的内容")
        return BLOCK

    receivers = load_receivers()
    if not receivers:
        await session.send("当前没有配置反馈接收频道")
        return BLOCK

    content = _format_feedback_message(session, text)
    data = FeedbackData(
        platform=session.account.platform,
        self_id=session.account.self_id,
        channel_id=session.channel.id,
        guild_id=session.event.guild.id if session.event.guild else None,
    )

    sent = 0
    for index, receiver in enumerate(receivers):
        if index and config.broadcast_delay > 0:
            await sleep(config.broadcast_delay)

        account = _find_account(receiver.platform, receiver.self_id)
        if account is None:
            logger.warning(
                f"cannot find account ({receiver.platform}:{receiver.self_id})"
            )
            continue

        try:
            receipts = await account.protocol.send_message(
                receiver.channel_id,
                content,
            )
        except (ActionFailed, ServerException) as e:
            logger.warning(f"send feedback failed: {e}")
            continue

        sent += 1
        for receipt in receipts:
            save_feedback(receipt.id, data)

    if sent:
        await session.send("反馈已发送")
    else:
        await session.send("反馈发送失败：没有可用的接收频道")
    return BLOCK


@on(MessageCreatedEvent, priority=20)
async def reply_feedback(session: Session[MessageCreatedEvent]):
    quote = session.event.quote
    if quote is None or quote.id is None:
        return

    data = get_feedback(quote.id)
    if data is None:
        return

    content = session.elements
    if not content.extract_plain_text().strip():
        return

    content.insert(0, Quote(quote.id))

    account = _find_account(data.platform, data.self_id)
    if account is None:
        logger.warning(f"cannot find account ({data.platform}:{data.self_id})")
        return

    try:
        await account.protocol.send_message(data.channel_id, content)
    except (ActionFailed, ServerException) as e:
        logger.warning(f"reply feedback failed: {e}")
        return

    delete_feedback(quote.id)
    return BLOCK
