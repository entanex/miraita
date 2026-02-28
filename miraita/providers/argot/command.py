from collections.abc import AsyncGenerator, Awaitable, Callable, Generator
from typing import overload, TypeAlias, TypeVar

from arclet.alconna import Alconna
from arclet.letoderea import Subscriber, Propagator, STOP
from arclet.entari import Session, MessageChain, command, plugin
from arclet.entari.event.base import ReactionAddedEvent

from .provider import ArgotProvider


_BaseM: TypeAlias = str | MessageChain | None
_M: TypeAlias = (
    _BaseM
    | Generator[_BaseM, None, None]
    | AsyncGenerator[_BaseM, None]
    | Awaitable[_BaseM]
)
TM = TypeVar("TM", bound=_M)


class ReactionPropagator(Propagator):
    def __init__(self, emoji_ids: list[str]):
        self.emoji_ids = emoji_ids

    def before(self, session: Session[ReactionAddedEvent]):
        content = session.event.message.content
        emoji_id = content.split("|")[1]
        if emoji_id not in self.emoji_ids:
            return STOP

    def compose(self):
        yield self.before, True


@overload
def on_argot(cmd: str) -> Callable[[Callable[..., TM]], Subscriber[TM]]: ...


@overload
def on_argot(cmd: Alconna) -> Callable[[Callable[..., TM]], Subscriber[TM]]: ...


def on_argot(cmd: str | Alconna) -> Callable[[Callable[..., TM]], Subscriber[TM]]:
    if isinstance(cmd, str):
        _command = command.command(cmd, providers=[ArgotProvider])
        _command.meta.hide = True
    else:
        cmd.meta.hide = True
        _command = command.on(cmd, providers=[ArgotProvider])

    return _command


def on_reaction(emoji_ids: list[str]):
    return plugin.listen(
        ReactionAddedEvent,
        providers=[ArgotProvider],
        propagators=[ReactionPropagator(emoji_ids)],
    )
