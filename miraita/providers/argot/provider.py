from satori import EventType
from arclet.letoderea import Provider, Contexts, STOP
from arclet.entari.const import ITEM_MESSAGE_REPLY, ITEM_ORIGIN_EVENT

from .element import Argot
from .data_source import get_argot_by_message_id


class ArgotProvider(Provider[Argot]):
    async def __call__(self, context: Contexts) -> Argot:
        if reply := context.get(ITEM_MESSAGE_REPLY):
            message_id = reply.quote.id
        elif event := context.get(ITEM_ORIGIN_EVENT):
            if event.type != EventType.REACTION_ADDED:
                raise STOP

            if event.message is None:
                raise STOP

            message_id = event.message.id
        else:
            raise STOP

        if message_id is None:
            raise STOP

        argot = await get_argot_by_message_id(message_id)

        if argot is None or argot.is_expired:
            raise STOP

        return Argot(argot.name, argot.data, argot.expired_at)
