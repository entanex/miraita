import random
from collections.abc import Awaitable, Iterable, Mapping
from typing import Any

from arclet.entari import At, MessageChain, MessageCreatedEvent, Session

from ._types import ActionConfig, RepeatAction, RepeatState, StateCallback, StateResult


def state_key(
    platform: str,
    self_id: str,
    channel_id: str,
    guild_id: str | None = None,
) -> str:
    return f"{platform}:{self_id}:{guild_id or ''}:{channel_id}"


def normalize_message(message: MessageChain | str) -> str:
    return str(message).strip()


def update_repeated_state(state: RepeatState, content: str):
    state.repeated = True
    if state.content == content:
        state.times += 1
        return

    state.content = content
    state.times = 1
    state.users.clear()


def _coerce_action(action: RepeatAction | Mapping[str, Any]) -> RepeatAction:
    if isinstance(action, RepeatAction):
        return action
    return RepeatAction(**dict(action))


def _iter_actions(actions: ActionConfig) -> Iterable[RepeatAction]:
    if actions is None:
        return ()
    if isinstance(actions, RepeatAction | Mapping):
        return (_coerce_action(actions),)
    return (_coerce_action(action) for action in actions)


def _format_reply(
    template: str,
    state: RepeatState,
    session: Session[MessageCreatedEvent],
) -> str | MessageChain:
    values = {
        "content": state.content,
        "times": str(state.times),
        "user_id": session.user.id,
        "user_name": session.user.name or session.user.id,
        "self_id": session.account.self_id,
        "channel_id": session.channel.id,
        "guild_id": session.event.guild.id if session.event.guild else "",
    }

    def render_text(text: str):
        for key, value in values.items():
            text = text.replace("{" + key + "}", value)
        return text

    if "{at_user}" not in template:
        return render_text(template)

    chain = MessageChain()
    parts = template.split("{at_user}")
    for index, part in enumerate(parts):
        if part:
            chain.append(render_text(part))
        if index < len(parts) - 1:
            chain.append(At(session.user.id, name=session.user.name))
    return chain


def _check_action(
    action: RepeatAction,
    state: RepeatState,
    session: Session[MessageCreatedEvent],
    default_reply: str | None,
    default_repeated: bool | None,
) -> StateResult:
    if state.times < action.min_times:
        return None
    if action.content is not None and state.content != action.content:
        return None
    if action.user_times and state.users.get(session.user.id, 0) < action.user_times:
        return None

    repeated = action.repeated if action.repeated is not None else default_repeated
    if repeated is not None and state.repeated != repeated:
        return None
    if random.random() >= max(0, min(action.probability, 1)):
        return None

    reply = action.reply if action.reply is not None else default_reply
    if reply is None:
        return None
    return _format_reply(reply, state, session)


def check_actions(
    actions: ActionConfig,
    state: RepeatState,
    session: Session[MessageCreatedEvent],
    default_reply: str | None,
    default_repeated: bool | None = None,
) -> StateResult:
    for action in _iter_actions(actions):
        reply = _check_action(action, state, session, default_reply, default_repeated)
        if reply:
            return reply
    return None


async def _check_callback(
    callback: StateCallback | None,
    state: RepeatState,
    session: Session[MessageCreatedEvent],
) -> StateResult:
    if callback is None:
        return None

    result = callback(state, session)
    if isinstance(result, Awaitable):
        return await result
    return result


async def check_callbacks(
    callbacks: Iterable[StateCallback],
    state: RepeatState,
    session: Session[MessageCreatedEvent],
) -> StateResult:
    for callback in callbacks:
        reply = await _check_callback(callback, state, session)
        if reply:
            return reply
    return None
