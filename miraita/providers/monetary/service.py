from launart import Launart, Service
from launart.status import Phase
from arclet.entari import add_service
from entari_plugin_database import get_session as get_db_session
from sqlalchemy import select

from miraita.databases import Monetary as MonetaryModel


class Monetary(Service):
    id = "miriata/monetary"

    @property
    def required(self):
        return set()

    @property
    def stages(self) -> set[Phase]:
        return {"preparing", "blocking", "cleanup"}

    def __init__(self):
        super().__init__()

    async def get(self, user_id: int, currency: str = "default") -> int:
        async with get_db_session() as db_session:
            stmt = select(MonetaryModel.value).where(
                MonetaryModel.id == user_id,
                MonetaryModel.currency == currency,
            )
            return await db_session.scalar(stmt) or 0

    async def cost(self, user_id: int, cost: int, currency: str = "default") -> int:
        async with get_db_session() as db_session:
            stmt = select(MonetaryModel).where(
                MonetaryModel.id == user_id,
                MonetaryModel.currency == currency,
            )
            row = await db_session.scalar(stmt)
            if row is None or row.value < cost:
                raise ValueError("insufficient balance")

            row.value -= cost
            await db_session.commit()
        return cost

    async def gain(self, user_id: int, gain: int, currency: str = "default") -> int:
        async with get_db_session() as db_session:
            stmt = select(MonetaryModel).where(
                MonetaryModel.id == user_id,
                MonetaryModel.currency == currency,
            )
            row = await db_session.scalar(stmt)
            if row is None:
                db_session.add(MonetaryModel(id=user_id, currency=currency, value=gain))
            else:
                row.value += gain
            await db_session.commit()
        return gain

    async def launch(self, manager: Launart):
        async with self.stage("preparing"):
            pass

        async with self.stage("blocking"):
            await manager.status.wait_for_sigexit()

        async with self.stage("cleanup"):
            pass


monetary = Monetary()
add_service(monetary)
