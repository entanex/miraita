from arclet.entari import Plugin, Session

plugin = Plugin.current()


@plugin.use("::before_send")
async def send_hook(session: Session | None = None) -> None:
    if session is None:
        return

    at, reply = session._resolve(True, True)

    if at:
        session.elements.insert(0, at)
    if reply:
        session.elements.insert(0, reply)

    return None
