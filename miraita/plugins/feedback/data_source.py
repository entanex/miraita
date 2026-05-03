from dataclasses import asdict, dataclass

from miraita.providers.datastore import datastore


@dataclass
class Receiver:
    platform: str
    self_id: str
    channel_id: str
    guild_id: str | None


@dataclass
class FeedbackData:
    platform: str
    self_id: str
    channel_id: str
    guild_id: str | None


def _parse_receiver(data: object) -> Receiver | None:
    if not isinstance(data, dict):
        return None
    if not isinstance(data.get("platform"), str):
        return None
    if not isinstance(data.get("self_id"), str):
        return None
    if not isinstance(data.get("channel_id"), str):
        return None
    if data.get("guild_id") is not None and not isinstance(data.get("guild_id"), str):
        return None
    return Receiver(
        platform=data["platform"],
        self_id=data["self_id"],
        channel_id=data["channel_id"],
        guild_id=data.get("guild_id"),
    )


def _parse_feedback_data(data: object) -> FeedbackData | None:
    if not isinstance(data, dict):
        return None
    if not isinstance(data.get("platform"), str):
        return None
    if not isinstance(data.get("self_id"), str):
        return None
    if not isinstance(data.get("channel_id"), str):
        return None
    if data.get("guild_id") is not None and not isinstance(data.get("guild_id"), str):
        return None
    return FeedbackData(
        platform=data["platform"],
        self_id=data["self_id"],
        channel_id=data["channel_id"],
        guild_id=data.get("guild_id"),
    )


def load_receivers() -> list[Receiver]:
    receivers = datastore.get("receivers", [])
    if not isinstance(receivers, list):
        return []
    return [
        receiver
        for data in receivers
        if (receiver := _parse_receiver(data)) is not None
    ]


def save_receivers(receivers: list[Receiver]) -> None:
    datastore.set("receivers", [asdict(receiver) for receiver in receivers])


def _load_feedbacks() -> dict[str, FeedbackData]:
    feedbacks = datastore.get("feedbacks", {})
    if not isinstance(feedbacks, dict):
        return {}

    valid_feedbacks: dict[str, FeedbackData] = {}
    for message_id, data in feedbacks.items():
        if not isinstance(message_id, str):
            continue
        feedback_data = _parse_feedback_data(data)
        if feedback_data is None:
            continue
        valid_feedbacks[message_id] = feedback_data

    if len(valid_feedbacks) != len(feedbacks):
        _save_feedbacks(valid_feedbacks)

    return valid_feedbacks


def _save_feedbacks(feedbacks: dict[str, FeedbackData]) -> None:
    datastore.set(
        "feedbacks",
        {
            message_id: asdict(feedback_data)
            for message_id, feedback_data in feedbacks.items()
        },
    )


def save_feedback(message_id: str, data: FeedbackData) -> None:
    feedbacks = _load_feedbacks()
    feedbacks[message_id] = data
    _save_feedbacks(feedbacks)


def get_feedback(message_id: str) -> FeedbackData | None:
    feedbacks = _load_feedbacks()
    return feedbacks.get(message_id)


def delete_feedback(message_id: str) -> None:
    feedbacks = _load_feedbacks()
    if message_id not in feedbacks:
        return
    feedbacks.pop(message_id)
    _save_feedbacks(feedbacks)
