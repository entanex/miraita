from arclet.letoderea import Provider, Contexts
from arclet.entari.event.base import Reply

from .element import Argot
from .data_source import get_argot_by_message_id


class ArgotProvider(Provider[Argot]):
    async def __call__(self, context: Contexts) -> Argot | None:
        reply: Reply | None = context.get("$message_reply")
        if reply is None or reply.quote.id is None:
            return None

        message_id = reply.quote.id
        argot = await get_argot_by_message_id(message_id)

        if argot is None or argot.is_expired:
            return None

        return Argot(argot.name, argot.data, argot.expired_at)
