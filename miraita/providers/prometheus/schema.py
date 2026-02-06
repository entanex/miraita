from dataclasses import dataclass


@dataclass
class BotInfo:
    bot_id: str
    platform: str
    status: str
    shutdown_count: int


@dataclass
class BotStatusResponse:
    total_bots: int
    bots: list[BotInfo]
    error: str | None = None


@dataclass
class BotMessageStats:
    bot_id: str
    platform: str
    count: float


@dataclass
class MessageStatsResponse:
    total_received: float
    total_sent: float
    received_by_bot: dict[str, BotMessageStats]
    sent_by_bot: dict[str, BotMessageStats]
    error: str | None = None


@dataclass
class MatcherStats:
    plugin_name: str
    call_count: float
    total_duration: float
    avg_duration: float


@dataclass
class MatcherStatsResponse:
    total_matchers: int
    top_matchers: list[MatcherStats]
    total_calls: int
    error: str | None = None


@dataclass
class SystemMetricsResponse:
    uptime: str
    start_time: str
    uptime_seconds: float
    error: str | None = None
