from arclet.entari import Plugin, Session, MessageCreatedEvent

plugin = Plugin.current()


@plugin.use("::before_send")
async def send_hook(session: Session[MessageCreatedEvent] | None = None) -> None:
    if session is None:
        return

    _, reply = session._resolve(False, True)

    if reply:
        session.elements.insert(0, reply)

    return None
