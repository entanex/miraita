from collections.abc import Iterable

from satori import EventType

SUPPORTED_EVENTS = (
    EventType.GUILD_MEMBER_ADDED.value,
    EventType.GUILD_MEMBER_REMOVED.value,
    EventType.GUILD_MEMBER_REQUEST.value,
)


def resolve_events(events: Iterable[str]) -> tuple[set[str], set[str]]:
    resolved: set[str] = set()
    invalid: set[str] = set()

    for raw in events:
        event = raw.strip().lower()
        if not event:
            continue
        if event == "all":
            resolved.update(SUPPORTED_EVENTS)
            continue
        try:
            normalized = EventType(event).value
        except ValueError:
            invalid.add(raw)
            continue
        if normalized in SUPPORTED_EVENTS:
            resolved.add(normalized)
        else:
            invalid.add(raw)

    return resolved, invalid
