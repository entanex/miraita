from arclet.entari import Plugin, Session

from .element import Sticker

plugin = Plugin.current()


@plugin.use("::before_send")
async def _save_argot(session: Session | None = None) -> None:
    if session is None:
        return

    if not session.elements.has(Sticker):
        return

    session.elements[:] = [
        el.to_image() if isinstance(el, Sticker) else el for el in session.elements
    ]

    return None
