from collections import deque

from arclet.entari import MessageChain, MessageCreatedEvent, filter_
from arclet.entari.config import config_model_validate
from arclet.entari.event.config import ConfigReload
from arclet.entari.event.send import SendResponse
from arclet.letoderea import BLOCK, on
from arclet.letoderea.context import Contexts
from entari_plugin_user import UserSession

from miraita.utils.reaction import with_reaction
from miraita.providers.llm.exception import ModelNotFoundError
from miraita.providers.llm.config import Config, _conf

from .manager import LLMSessionManager

RECORD = deque(maxlen=16)


@on(SendResponse)
async def _record(event: SendResponse):
    if event.result and event.session:
        RECORD.append(event.session.event.sn)


@on(ConfigReload)
async def reload_config(event: ConfigReload):
    if event.scope != "plugin":
        return
    if event.key not in ("entari_plugin_llm", "llm"):
        return
    new_conf = config_model_validate(Config, event.value)
    _conf.models = new_conf.models
    _conf.prompt = new_conf.prompt
    _conf.tools = new_conf.tools


if _conf.enable_direct_message:

    @on(MessageCreatedEvent, priority=1000).if_(filter_.direct_message)
    @with_reaction
    async def run_conversation(session: UserSession, ctx: Contexts):
        if session.internal.event.sn in RECORD:
            return BLOCK

        try:
            answer = await LLMSessionManager.chat(
                session.elements,
                session=session,
                ctx=ctx,
            )
            if answer != "[END_OF_RESPONSE]":
                await session.send(answer)
        except ModelNotFoundError as e:
            await session.send(MessageChain(str(e)))
        except Exception as e:
            await session.send(MessageChain(str(e)))
        return BLOCK
