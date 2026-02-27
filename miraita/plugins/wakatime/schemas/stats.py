from typing_extensions import TypedDict


class Categories(TypedDict):
    name: str
    total_seconds: float
    percent: float
    digital: str
    decimal: str
    text: str
    hours: int
    minutes: int


class Project(TypedDict):
    name: str
    total_seconds: float
    percent: float
    digital: str
    decimal: str
    text: str
    hours: int
    minutes: int


class Languages(TypedDict):
    name: str
    total_seconds: float
    percent: float
    digital: str
    decimal: str
    text: str
    hours: int
    minutes: int
    seconds: int | None


class Editors(TypedDict):
    name: str
    total_seconds: float
    percent: float
    digital: str
    decimal: str
    text: str
    hours: int
    minutes: int
    seconds: int | None


class OperatingSystems(TypedDict):
    name: str
    total_seconds: float
    percent: float
    digital: str
    decimal: str
    text: str
    hours: int
    minutes: int


class Machines(TypedDict):
    name: str
    total_seconds: float
    percent: float
    digital: str
    decimal: str
    text: str
    hours: int
    minutes: int
    machine_name_id: str


class GrandTotal(TypedDict):
    decimal: str
    digital: str
    hours: int
    minutes: int
    text: str
    total_seconds: float


class Stats(TypedDict):
    human_readable_total: str
    human_readable_total_including_other_language: str
    daily_average: float
    daily_average_including_other_language: float
    human_readable_daily_average: str
    human_readable_daily_average_including_other_language: str
    categories: list[Categories] | None
    projects: list[Project] | None
    languages: list[Languages] | None
    editors: list[Editors] | None
    operating_systems: list[OperatingSystems] | None
    machines: list[Machines] | None
    user_id: str
    username: str
    is_up_to_date: bool


class StatsBar(TypedDict):
    grand_total: GrandTotal
    categories: list[Categories] | None
    projects: list[Project] | None
    editors: list[Editors] | None
    languages: list[Languages] | None
    operating_systems: list[OperatingSystems] | None
