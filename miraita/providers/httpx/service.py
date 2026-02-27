from typing import cast

from httpx import AsyncClient, Timeout
from launart import Launart, Service
from launart.status import Phase
from arclet.entari import add_service


class HttpxClientService(Service):
    id = "miraita.provider/httpx"
    session: AsyncClient

    def __init__(self, session: AsyncClient | None = None) -> None:
        self.session = cast(AsyncClient, session)
        super().__init__()

    @property
    def stages(self) -> set[Phase]:
        return {"preparing", "blocking", "cleanup"}

    @property
    def required(self):
        return set()

    async def launch(self, manager: Launart):
        async with self.stage("preparing"):
            if self.session is None:
                self.session = AsyncClient(timeout=Timeout(None))
        async with self.stage("blocking"):
            await manager.status.wait_for_sigexit()
        async with self.stage("cleanup"):
            await self.session.aclose()


add_service(HttpxClientService)
