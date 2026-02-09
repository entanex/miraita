import json
import time
from dataclasses import dataclass, field, asdict
from typing import Any, TYPE_CHECKING
from typing_extensions import Self

from arclet.entari import local_data

if TYPE_CHECKING:
    from .element import Argot


@dataclass
class ArgotData:
    name: str
    message_id: str
    data: dict[str, Any] = field(default_factory=dict)
    expired_at: int | None = None

    @property
    def is_expired(self) -> bool:
        if self.expired_at is None:
            return False
        return int(time.time()) > self.expired_at

    @classmethod
    def from_element(cls, el: "Argot", message_id: str) -> Self:
        return cls(
            name=el.name,
            message_id=message_id,
            data=el.data or {},
            expired_at=el.expired_at,
        )

    def to_json(self) -> dict:
        return asdict(self)


async def _load_all_argot() -> list[ArgotData]:
    file = local_data.get_data_file("argot", "data.json")
    try:
        with open(file, encoding="utf-8") as f:
            raw_data = json.load(f)
            if not isinstance(raw_data, list):
                return []
            return [ArgotData(**item) for item in raw_data]
    except (FileNotFoundError, json.JSONDecodeError, TypeError):
        return []


async def _save_all_argot(data: list[ArgotData]):
    file = local_data.get_data_file("argot", "data.json")
    file.parent.mkdir(parents=True, exist_ok=True)

    serializable_data = [asdict(item) for item in data]

    with open(file, "w", encoding="utf-8") as f:
        json.dump(serializable_data, f, ensure_ascii=False, indent=2)


async def get_argot_by_name(name: str) -> ArgotData | None:
    all_argot = await _load_all_argot()
    return next((a for a in all_argot if a.name == name), None)


async def get_argot_by_message_id(message_id: str) -> ArgotData | None:
    all_argot = await _load_all_argot()
    return next((a for a in all_argot if a.message_id == message_id), None)


async def save_argot(argot: ArgotData) -> None:
    all_argot = await _load_all_argot()

    for i, existing in enumerate(all_argot):
        if existing.name == argot.name:
            all_argot[i] = argot
            break
    else:
        all_argot.append(argot)

    await _save_all_argot(all_argot)


async def delete_argot(name: str) -> bool:
    all_argot = await _load_all_argot()
    initial_len = len(all_argot)

    all_argot = [a for a in all_argot if a.name != name]

    if len(all_argot) < initial_len:
        await _save_all_argot(all_argot)
        return True
    return False
