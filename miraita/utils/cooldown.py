from datetime import datetime

from arclet.entari import Session, MessageChain
from arclet.letoderea import STOP, Propagator, propagate
from arclet.letoderea.utils import TCallable
from entari_plugin_database import get_session as get_db_session
from entari_plugin_user import get_user
from sqlalchemy import case, select, update
from sqlalchemy.dialects.sqlite import insert

from miraita.databases import Interval as IntervalModel
from miraita.databases import Semaphore as SemaphoreModel

LimitPrompt = str | MessageChain | None


async def _user_id(session: Session | None) -> int | None:
    if session is None:
        return None

    user = await get_user(
        session.account.platform,
        session.user,
    )
    return user.id


def _prompt_text(prompt: LimitPrompt) -> str | None:
    return prompt.extract_plain_text() if isinstance(prompt, MessageChain) else prompt


class interval(Propagator):
    def __init__(
        self,
        value: float,
        limit_prompt: LimitPrompt = None,
        priority: int = 80,
    ):
        if value < 0:
            raise ValueError("interval value must be non-negative")
        self.success = True
        self.value = value
        self.limit_prompt = limit_prompt
        self.priority = priority
        self.name: str | None = None

    async def before(self, session: Session | None = None):
        user_id = await _user_id(session)
        if user_id is None or self.name is None:
            return STOP

        async with get_db_session() as db_session:
            stmt = select(IntervalModel.last_time).where(
                IntervalModel.id == user_id,
                IntervalModel.name == self.name,
            )
            last_time = await db_session.scalar(stmt)

        if last_time is None:
            return

        self.success = (datetime.now() - last_time).total_seconds() > self.value
        if not self.success:
            if session and self.limit_prompt:
                await session.send(self.limit_prompt)
            return STOP

    async def after(self, session: Session | None = None):
        user_id = await _user_id(session)
        if user_id is None or self.name is None:
            return

        now = datetime.now()
        stmt = insert(IntervalModel).values(
            id=user_id,
            name=self.name,
            value=self.value,
            last_time=now,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[IntervalModel.id, IntervalModel.name],
            set_={
                "value": self.value,
                "last_time": now,
            },
        )
        async with get_db_session() as db_session:
            await db_session.execute(stmt)
            await db_session.commit()

    def compose(self):
        yield self.before, True, self.priority
        yield self.after, False, self.priority

    def __call__(self, func: TCallable) -> TCallable:
        self.name = f"{func.__module__}.{func.__qualname__}"
        return propagate(self)(func)


class semaphore(Propagator):
    def __init__(
        self,
        count: int,
        limit_prompt: LimitPrompt = None,
        priority: int = 80,
    ):
        if count < 1:
            raise ValueError("semaphore count must be positive")
        self.count = count
        self.limit_prompt = limit_prompt
        self.priority = priority
        self.name: str | None = None

    async def before(self, session: Session | None = None):
        user_id = await _user_id(session)
        if user_id is None or self.name is None:
            return STOP

        stmt = insert(SemaphoreModel).values(
            id=user_id,
            name=self.name,
            count=self.count,
            value=1,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[SemaphoreModel.id, SemaphoreModel.name],
            set_={
                "count": self.count,
                "value": SemaphoreModel.value + 1,
            },
            where=SemaphoreModel.value < self.count,
        ).returning(SemaphoreModel.value)
        async with get_db_session() as db_session:
            result = await db_session.execute(stmt)
            acquired = result.scalar_one_or_none() is not None
            await db_session.commit()

        if not acquired:
            if session and self.limit_prompt:
                await session.send(self.limit_prompt)
            return STOP

    async def after(self, session: Session | None = None):
        user_id = await _user_id(session)
        if user_id is None or self.name is None:
            return

        stmt = (
            update(SemaphoreModel)
            .where(
                SemaphoreModel.id == user_id,
                SemaphoreModel.name == self.name,
            )
            .values(
                value=case(
                    (SemaphoreModel.value > 0, SemaphoreModel.value - 1),
                    else_=0,
                )
            )
        )
        async with get_db_session() as db_session:
            await db_session.execute(stmt)
            await db_session.commit()

    def compose(self):
        yield self.before, True, self.priority
        yield self.after, False, self.priority

    def __call__(self, func: TCallable) -> TCallable:
        self.name = f"{func.__module__}.{func.__qualname__}"
        return propagate(self)(func)
