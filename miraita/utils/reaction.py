from arclet.letoderea import Propagator, propagate
from arclet.entari import Session, MessageCreatedEvent, ChannelType


class ReactionPropagator(Propagator):
    def __init__(self):
        self.waiting_emoji = ["424", "👀"]
        self.success_emoji = ["375", "🎉"]
        self.emoji = None

    def _get_emoji_index(self, session: Session[MessageCreatedEvent]):
        return 0 if session.account.platform in ["onebot", "milky", "llonebot"] else 1

    async def prepare(self, session: Session[MessageCreatedEvent]):
        if session.channel.type == ChannelType.DIRECT:
            return

        self.emoji = self.waiting_emoji[self._get_emoji_index(session)]

        await session.reaction_create(
            self.emoji,
            session.event.message.id,
        )

    async def finish(self, session: Session[MessageCreatedEvent]):
        if self.emoji:
            await session.reaction_delete(self.emoji)

        await session.reaction_create(
            self.success_emoji[self._get_emoji_index(session)],
            session.event.message.id,
        )

    def compose(self):
        yield self.prepare, True, 100
        yield self.finish, False, 100


with_reaction = propagate(ReactionPropagator())
