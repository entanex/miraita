from arclet.alconna import (
    Alconna,
    Args,
    MultiVar,
    Option,
    Subcommand,
    CommandMeta,
    Namespace,
    store_true,
    config,
)
from arclet.entari import MessageChain, command, metadata
from arclet.entari.const import ITEM_MESSAGE_REPLY
from arclet.letoderea import BLOCK, Contexts
from entari_plugin_user import UserSession

from miraita.utils.reaction import with_reaction
from miraita.providers.llm._jsondata import set_default_model
from miraita.providers.llm.exception import ModelNotFoundError
from miraita.providers.llm.config import get_model_config, get_model_id, get_model_list

from . import chat as chat
from .manager import LLMSessionManager
from .utils import render_model_list, render_session_list, select_session

metadata(
    name="LLM",
    author=[
        {"name": "RF-Tar-Railt", "email": "rf_tar_railt@qq.com"},
        {"name": "Komorebi", "email": "mute231010@gmail.com"},
    ],
    description="LLM 聊天",
    classifier=["AI", "工具"],
)

ns = Namespace("LLM")
config.namespaces["LLM"] = ns

llm_alc = Alconna(
    "llm",
    Args["content?#内容", MultiVar(str)],
    Option(
        "-m|--model",
        Args["model?#模型名称", str],
        dest="model_opt",
        help_text="指定模型",
    ),
    Option(
        "-n|--new",
        dest="new_opt",
        default=False,
        action=store_true,
        help_text="创建新会话",
    ),
    Subcommand("new", dest="new_cmd", help_text="创建新会话"),
    Subcommand("switch", Args["session_id?#会话ID", str], help_text="切换会话"),
    Subcommand("delete", Args["session_id?#会话ID", str], help_text="删除会话"),
    Subcommand(
        "session",
        Option("-l|--list", help_text="查看会话列表"),
        help_text="查看当前会话信息",
    ),
    Subcommand(
        "model",
        Args["model?#模型名称", str],
        Option("-l|--list", help_text="查看模型列表"),
        dest="model_cmd",
        help_text="查看当前模型信息",
    ),
    meta=CommandMeta(
        description="LLM 聊天",
        usage="/llm [-m [MODEL<str>]] [-n]",
        example="/llm hello",
    ),
    namespace=ns,
)

llm_alc.shortcut("ai", {"command": "llm", "fuzzy": True, "prefix": True})

llm_disp = command.mount(llm_alc).as_execute()


@llm_disp.handle(priority=25)
@with_reaction
async def llm_chat(
    ctx: Contexts,
    session: UserSession,
    content: command.Match[MessageChain],
    new_opt: command.Query[bool] = command.Query("new_opt.value"),
    model_opt: command.Query[str] = command.Query("model_opt.model"),
):
    user_prompt = MessageChain([])

    if reply := ctx.get(ITEM_MESSAGE_REPLY):
        user_prompt += reply.origin.message

    if content.available:
        user_prompt += content.result

    if not user_prompt:
        resp = await session.internal.prompt("需要我为你做些什么？")
        if not resp:
            return BLOCK
        user_prompt = resp

    try:
        answer = await LLMSessionManager.chat(
            user_prompt,
            ctx=ctx,
            session=session,
            model=model_opt.result if model_opt.available else None,
            new=new_opt.result,
        )
        if answer != "[END_OF_RESPONSE]":
            return BLOCK.finish(answer)
    except ModelNotFoundError as e:
        return BLOCK.finish(MessageChain(str(e)))
    except Exception as e:
        return BLOCK.finish(MessageChain(str(e)))


@llm_disp.assign("new_cmd")
async def create_session(session: UserSession):
    new_session = await LLMSessionManager.create_new_session(session.user)
    return BLOCK.finish(f"以创建并切换到新会话\n会话ID: {new_session.session_id}")


@llm_disp.assign("switch")
async def switch_session(session: UserSession, session_id: command.Match[str]):
    if not session_id.available:
        selected = await select_session(session)
        if selected is None:
            return BLOCK

        session_id.result = selected

    switched = await LLMSessionManager.switch(session.user, session_id.result)
    return BLOCK.finish("切换成功" if switched else "未找到对应会话")


@llm_disp.assign("delete")
async def delete_session(session: UserSession, session_id: command.Match[str]):
    if not session_id.available:
        selected = await select_session(session)
        if selected is None:
            return BLOCK

        session_id.result = selected

    info = await LLMSessionManager.get_current_session_info(session.user)
    deleted = await LLMSessionManager.delete(session.user, session_id.result)
    if deleted:
        rows = await LLMSessionManager.list_sessions(session.user)
        if not rows:
            await LLMSessionManager.create_new_session(session.user)
            return BLOCK.finish("删除成功，已自动创建新会话")
        elif info and info["session_id"] == session_id.result:
            await LLMSessionManager.switch(session.user, rows[0].session_id)
            return BLOCK.finish("删除成功，已自动切换到最近的会话")
        else:
            return BLOCK.finish(
                "删除成功，当前会话列表：\n" + render_session_list(rows)
            )
    else:
        return BLOCK.finish("未找到对应会话")


@llm_disp.assign("session", priority=20)
async def session_info(session: UserSession):
    info = await LLMSessionManager.get_current_session_info(session.user)
    if info is None:
        return BLOCK.finish("当前没有活动会话")

    created_at = info["created_at"].strftime("%Y-%m-%d %H:%M:%S")
    return BLOCK.finish(
        "\n".join(
            [
                f"会话ID: {info['session_id']}",
                f"话题: {info['topic']}",
                f"消息数: {info['message_count']}",
                f"累计 Token: {info['total_tokens']}",
                f"创建时间: {created_at}",
            ]
        )
    )


@llm_disp.assign("session.list")
async def list_sessions(session: UserSession):
    rows = await LLMSessionManager.list_sessions(session.user)

    if not rows:
        return BLOCK.finish("暂无会话")

    return BLOCK.finish(render_session_list(rows))


@llm_disp.assign("model_cmd", priority=20)
async def model_cmd(session: UserSession, model: command.Match[str]):
    if model.available:
        if model.result not in get_model_list():
            return BLOCK.finish(render_model_list())

        conf = get_model_config(model.result)
        set_default_model(get_model_id(conf))

        return BLOCK.finish(f"已切换默认模型: {get_model_id(conf)}")

    conf = get_model_config()
    return BLOCK.finish(render_model_list())


@llm_disp.assign("model_cmd.list")
async def list_models(session: UserSession):
    return BLOCK.finish(render_model_list())
