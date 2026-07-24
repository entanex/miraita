from dataclasses import dataclass
from typing import Any

from arclet.entari import MessageChain, Session
from arclet.entari.const import ITEM_ACCOUNT, ITEM_SESSION
from arclet.letoderea import Contexts, Result, define, provide

from .session import SessionInfo


@dataclass
class LLMCollectVariableEvent:
    session: Session
    llm_session: SessionInfo
    user_message: MessageChain

    def check_result(self, value) -> Result[dict[str, Any]] | None:
        if isinstance(value, dict):
            return Result(value)
        return None


collect_vars = define(LLMCollectVariableEvent, name="llm/collect_vars")
collect_vars.providers.extend(
    [
        provide(SessionInfo, call="$llm_session"),
        provide(MessageChain, call="$user_message"),
    ]
)


@collect_vars.gather
async def vars_gather(event: LLMCollectVariableEvent, context: Contexts):
    context[ITEM_ACCOUNT] = event.session.account
    context[ITEM_SESSION] = event.session
    context["$llm_session"] = event.llm_session
    context["$user_message"] = event.user_message
