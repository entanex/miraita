from satori import EventType
from arclet.letoderea import Provider, Contexts

from .element import Argot
from .data_source import get_argot_by_message_id


class ArgotProvider(Provider[Argot]):
    async def __call__(self, context: Contexts) -> Argot | None:
        if reply := context.get("$message_reply"):
            message_id = reply.quote.id
        elif event := context.get("$origin_event"):
            if event.type != EventType.REACTION_ADDED:
                return None
            message_id = event.message.id
        else:
            return None

        argot = await get_argot_by_message_id(message_id)

        if argot is None or argot.is_expired:
            return None

        return Argot(argot.name, argot.data, argot.expired_at)
