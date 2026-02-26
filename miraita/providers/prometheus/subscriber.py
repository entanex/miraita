import time
from arclet.letoderea import Propagator
from arclet.entari import Session

from .metrics import (
    matcher_calling_counter,
    matcher_duration_histogram,
)


class RecordRunningTime(Propagator):
    """A propagator to record running time."""

    def __init__(self, name: str):
        self.name = name
        self.start_time: float | None = None
        self.end_time: float | None = None

    async def prepare(self):
        """Prepare the propagator by setting the start time."""
        self.start_time = time.time()

    async def finish(self, session: Session | None = None):
        """Finish the propagator by setting the end time."""
        self.end_time = time.time()
        if session and self.start_time and self.end_time:
            matcher_calling_counter.labels(self.name).inc()
            matcher_duration_histogram.labels(self.name).observe(
                self.end_time - self.start_time
            )

    def compose(self):
        yield self.prepare, True, 0
        yield self.finish, False, 1000
