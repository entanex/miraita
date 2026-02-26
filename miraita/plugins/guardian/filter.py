from satori import EventType
from arclet.entari import Session
from arclet.letoderea import enter_if

from miraita.providers.datastore import datastore


async def check_subscribed(session: Session) -> bool:
    channel_id = session.channel.id
    event_type = EventType(session.type).value

    return event_type in datastore.get(channel_id, set())


is_subscribed = enter_if(check_subscribed)
