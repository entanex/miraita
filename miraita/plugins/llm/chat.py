from collections import deque

from arclet.entari import MessageCreatedEvent, filter_
from arclet.entari.config import config_model_validate
from arclet.entari.event.config import ConfigReload
from arclet.entari.event.send import SendResponse
from arclet.letoderea import BLOCK, on
from arclet.letoderea.typing import Contexts
from entari_plugin_user import UserSession

from miraita.providers.llm.config import Config, _conf

from .manager import LLMSessionManager

RECORD = deque(maxlen=16)


@on(SendResponse)
async def _record(event: SendResponse):
    if event.result and event.session:
        RECORD.append(event.session.event.sn)


@on(MessageCreatedEvent, priority=1000).if_(filter_.to_me)
async def run_conversation(session: UserSession, ctx: Contexts):
    if session.event.sn in RECORD:
        return BLOCK

    msg = session.internal.elements.extract_plain_text()
    answer = await LLMSessionManager.chat(user_input=msg, ctx=ctx, session=session)
    await session.send(answer)
    return BLOCK


@on(ConfigReload)
async def reload_config(event: ConfigReload):
    if event.scope != "plugin":
        return
    if event.key not in ("entari_plugin_llm", "llm"):
        return
    new_conf = config_model_validate(Config, event.value)
    _conf.models = new_conf.models
    _conf.prompt = new_conf.prompt
