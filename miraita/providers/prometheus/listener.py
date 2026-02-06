from arclet.entari.plugin import get_plugin_subscribers
from arclet.entari import Session, Plugin, MessageCreatedEvent, MessageChain

from satori.client import Account
from satori.model import LoginStatus, MessageReceipt

from .metrics import (
    miraita_start_at_gauge,
    bot_nums_gauge,
    bot_shutdown_counter,
    received_messages_counter,
    sent_messages_counter,
)
from .subscriber import RecordRunningTime

plugin = Plugin.current()


@plugin.use("::startup")
async def on_startup():
    miraita_start_at_gauge.set_to_current_time()


@plugin.use("::account_update")
async def on_account_update(account: Account, status: LoginStatus):
    if status == LoginStatus.CONNECT or status == LoginStatus.ONLINE:
        bot_nums_gauge.labels(account.self_id, account.platform).inc()
    elif status == LoginStatus.DISCONNECT or status == LoginStatus.OFFLINE:
        bot_nums_gauge.labels(account.self_id, account.platform).dec()
        bot_shutdown_counter.labels(account.self_id, account.platform).inc()


@plugin.dispatch(MessageCreatedEvent)
async def on_message_created(session: Session):
    received_messages_counter.labels(
        session.account.self_id, session.account.platform, session.user.id
    ).inc()


@plugin.use("::after_send")
async def on_after_send(
    account: Account,
    channel: str,
    message: MessageChain,
    result: list[MessageReceipt],
    session: "Session | None" = None,
):
    if session is None:
        return

    sent_messages_counter.labels(
        account.self_id, account.platform, session.user.id
    ).inc()


@plugin.use("::plugin/loaded_success")
async def on_pluin_load(plugin_id: str):
    if plugin_id == plugin.id:
        return
    subscribers = get_plugin_subscribers(plugin_id)
    for sub in subscribers:
        plugin.collect(
            sub.propagate(RecordRunningTime(f"{sub.callable_target.__module__}"))
        )
