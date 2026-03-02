import logging
from typing import Literal, TypeAlias
from arclet.entari.logger import log

LevelName: TypeAlias = Literal[
    "TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"
]

logger = log.wrapper("[miraita]").opt(colors=True)


class HealthCheckFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:  # pragma: no cover
        # complete query string (so parameter and other value included)
        args = record.args
        if not isinstance(args, tuple) or len(args) < 3 or not isinstance(args[2], str):
            # if args is not a tuple or does not have enough elements,
            # we assume it's not a health check request
            return True

        query_string = args[2]

        if query_string.startswith("/api/v1/health"):
            return False
        if query_string.startswith("/api/v1/metrics"):
            return False

        return True


logging.getLogger("uvicorn.access").addFilter(HealthCheckFilter())
