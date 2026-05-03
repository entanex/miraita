from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, TypeAlias

from arclet.entari import MessageChain, MessageCreatedEvent, Session

from .config import RepeatAction


@dataclass
class RepeatState:
    content: str = ""
    repeated: bool = False
    times: int = 0
    users: dict[str, int] = field(default_factory=dict)


StateResult: TypeAlias = str | MessageChain | None
StateCallback: TypeAlias = Callable[
    [RepeatState, Session[MessageCreatedEvent]], StateResult | Awaitable[StateResult]
]
ActionConfig: TypeAlias = (
    RepeatAction | Mapping[str, Any] | Sequence[RepeatAction | Mapping[str, Any]] | None
)
