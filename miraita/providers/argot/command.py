from collections.abc import AsyncGenerator, Awaitable, Callable, Generator
from typing import overload, TypeAlias, TypeVar

from arclet.alconna import Alconna
from arclet.letoderea import Subscriber
from arclet.entari import MessageChain, command

from .provider import ArgotProvider


_BaseM: TypeAlias = str | MessageChain | None
_M: TypeAlias = (
    _BaseM
    | Generator[_BaseM, None, None]
    | AsyncGenerator[_BaseM, None]
    | Awaitable[_BaseM]
)
TM = TypeVar("TM", bound=_M)


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
