from typing import overload

from arclet.alconna import Alconna
from arclet.alconna.tools.construct import alconna_from_format

from arclet.entari import Plugin
from arclet.entari.command.plugin import AlconnaPluginDispatcher


@overload
def on_argot(cmd: str) -> AlconnaPluginDispatcher: ...


@overload
def on_argot(cmd: Alconna) -> AlconnaPluginDispatcher: ...


def on_argot(cmd: str | Alconna) -> AlconnaPluginDispatcher:
    if isinstance(cmd, str):
        _command = alconna_from_format(cmd)
    else:
        _command = cmd

    _command.meta.hide = True

    if not (plugin := Plugin.current()):
        raise LookupError("no plugin context found")

    return AlconnaPluginDispatcher(
        plugin,
        _command,
        False,
        False,
        True,
    )
