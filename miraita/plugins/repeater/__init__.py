from arclet.entari import (
    ChannelType,
    MessageCreatedEvent,
    MessageChain,
    Session,
    metadata,
)
from arclet.entari.event.send import SendResponse
from arclet.letoderea import on

from ._types import RepeatState, StateCallback
from .config import Config, config
from .utils import (
    check_actions,
    check_callbacks,
    normalize_message,
    state_key,
    update_repeated_state,
)

from miraita.utils.no_reply import NoReply

metadata(
    name="复读机",
    author=[{"name": "Komorebi", "email": "mute231010@gmail.com"}],
    description="检测群聊复读并概率跟随复读",
    classifier=["娱乐"],
    config=Config,
)


_states: dict[str, RepeatState] = {}
_on_repeat_callbacks: list[StateCallback] = []
_on_interrupt_callbacks: list[StateCallback] = []


def on_repeat(callback: StateCallback) -> StateCallback:
    """注册自定义复读回调"""
    _on_repeat_callbacks.append(callback)
    return callback


def on_interrupt(callback: StateCallback) -> StateCallback:
    """注册自定义打断回调"""
    _on_interrupt_callbacks.append(callback)
    return callback


def _get_state(key: str) -> RepeatState:
    return _states.setdefault(key, RepeatState())


@on(SendResponse)
async def record_bot_message(event: SendResponse):
    if event.session is None:
        return
    if not event.result:
        return

    session = event.session
    if not isinstance(session.event, MessageCreatedEvent):
        return
    if not session.event.guild:
        return

    content = normalize_message(event.message)
    if not content:
        return

    key = state_key(
        event.account.platform,
        event.account.self_id,
        event.channel,
        session.event.guild.id,
    )
    update_repeated_state(_get_state(key), content)


@on(MessageCreatedEvent, priority=20)
async def handle_message(session: Session[MessageCreatedEvent]):
    if session.channel.type == ChannelType.DIRECT:
        return
    if not session.event.guild:
        return
    if session.user.id == session.account.self_id:
        return

    content = normalize_message(session.elements)
    if not content:
        return

    key = state_key(
        session.account.platform,
        session.account.self_id,
        session.channel.id,
        session.event.guild.id,
    )
    state = _get_state(key)

    if content == state.content:
        state.times += 1
        state.users[session.user.id] = state.users.get(session.user.id, 0) + 1

        reply = await check_callbacks(_on_repeat_callbacks, state, session)
        if not reply:
            reply = check_actions(
                config.on_repeat,
                state,
                session,
                "{content}",
                default_repeated=False,
            )
        if reply:
            await session.send(MessageChain(reply) + NoReply())
        return

    reply = await check_callbacks(_on_interrupt_callbacks, state, session)
    if not reply:
        reply = check_actions(config.on_interrupt, state, session, None)
    if reply:
        await session.send(MessageChain(reply) + NoReply())
        return

    state.content = content
    state.repeated = False
    state.times = 1
    state.users = {session.user.id: 1}
