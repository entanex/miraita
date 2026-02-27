from pathlib import Path
from typing_extensions import TypedDict

from .stats import Stats as Stats
from .users import Users as Users
from .stats import StatsBar as StatsBar


class WakaTime(TypedDict):
    user: Users
    stats: Stats
    stats_bar: StatsBar | None
    all_time_since_today: str
    background_image: str | Path
