from arclet.alconna import Alconna, Args, MultiVar, Option, Subcommand, store_true
from arclet.entari import Reply, Session, command, metadata
from arclet.letoderea import BLOCK, Contexts

from miraita.providers.llm._jsondata import set_default_model
from miraita.providers.llm.exception import ModelNotFoundError
from miraita.providers.llm.config import get_model_config, get_model_list

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

llm_alc = Alconna(
    "llm",
    Args["content?#内容", MultiVar(str)],
    Option("-m|--model", Args["model?#模型名称", str], help_text="指定模型"),
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
        help_text="查看当前模型信息",
    ),
)

llm_alc.shortcut("ai", {"command": "llm", "fuzzy": True, "prefix": True})

llm_disp = command.mount(llm_alc)


@llm_disp.handle(priority=25)
async def _(
    ctx: Contexts,
    session: Session,
    content: command.Match[tuple[str, ...]],
    new_opt: command.Query[bool] = command.Query("new_opt.value"),
    model: command.Query[str] = command.Query("model.model"),
):
    reply: Reply | None = ctx.get("$message_reply")

    user_input = " ".join(content.result) if content.available else ""

    if reply:
        user_input = f"{user_input} {reply.origin.content}".strip()

    if not user_input:
        resp = await session.prompt("需要我为你做些什么？")
        if not resp:
            await session.send("等待超时")
            return BLOCK
        user_input = resp.extract_plain_text()

    try:
        answer = await LLMSessionManager.chat(
            user_input=user_input,
            ctx=ctx,
            session=session,
            model=model.result if model.available else None,
            new=new_opt.result,
        )
        await session.send(answer)
    except ModelNotFoundError as e:
        await session.send(str(e))
    except Exception as e:
        await session.send(str(e))

    return BLOCK


@llm_disp.assign("new_cmd")
async def _(session: Session):
    new_session = await LLMSessionManager.create_new_session(session.user)
    await session.send(f"以创建并切换到新会话\n会话ID: {new_session.session_id}")
    return BLOCK


@llm_disp.assign("switch")
async def _(session: Session, session_id: command.Match[str]):
    if not session_id.available:
        selected = await select_session(session)
        if selected is None:
            return BLOCK

        session_id.result = selected

    switched = await LLMSessionManager.switch(session.user, session_id.result)
    await session.send("切换成功" if switched else "未找到对应会话")
    return BLOCK


@llm_disp.assign("delete")
async def _(session: Session, session_id: command.Match[str]):
    if not session_id.available:
        selected = await select_session(session)
        if selected is None:
            return BLOCK

        session_id.result = selected

    deleted = await LLMSessionManager.delete(session.user, session_id.result)
    if deleted:
        await LLMSessionManager.create_new_session(session.user)
        await session.send("删除成功，已自动创建新会话")
    else:
        await session.send("未找到对应会话")
    return BLOCK


@llm_disp.assign("session", priority=20)
async def _(session: Session):
    info = await LLMSessionManager.get_current_session_info(session.user)
    if info is None:
        await session.send("当前没有活动会话")
        return BLOCK

    created_at = info["created_at"].strftime("%Y-%m-%d %H:%M:%S")
    await session.send(
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
    return BLOCK


@llm_disp.assign("session.list")
async def _(session: Session):
    rows = await LLMSessionManager.list_sessions(session.user)

    if not rows:
        await session.send("暂无会话")
        return BLOCK

    await session.send(render_session_list(rows))
    return BLOCK


@llm_disp.assign("model", priority=20)
async def _(session: Session, model: command.Match[str]):
    if model.available:
        if model.result not in get_model_list():
            await session.send(render_model_list())
            return BLOCK

        conf = get_model_config(model.result)
        set_default_model(conf.name)

        await session.send(f"已切换默认模型: {conf.name}")
        return BLOCK

    conf = get_model_config()
    await session.send(render_model_list())
    return BLOCK


@llm_disp.assign("model.list")
async def _(session: Session):
    await session.send(render_model_list())
    return BLOCK
