from satori.model import MessageReceipt
from arclet.entari import MessageChain, Plugin, Session

from .element import Argot
from .data_source import save_argot, ArgotData

plugin = Plugin.current()


@plugin.use("::after_send")
async def _save_argot(
    result: list[MessageReceipt], session: Session | None = None
) -> None:
    if session is None:
        return

    if not session.elements.has(Argot):
        return

    argot: MessageChain[Argot] = session.elements.include(Argot)

    for item in argot:
        await save_argot(ArgotData.from_element(item, result[0].id))

    session.elements.exclude(Argot)

    return None
