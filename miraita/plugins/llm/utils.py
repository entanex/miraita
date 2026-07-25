from typing import Any
from collections.abc import Sequence

from entari_plugin_user import UserSession

from miraita.providers.llm.memory import UserMemory
from miraita.providers.llm._jsondata import get_default_model
from miraita.providers.llm.config import ScopedModel, _conf, get_model_config
from miraita.providers.llm.exception import ModelNotFoundError
from miraita.providers.llm.session import SessionInfo

from .manager import LLMSessionManager


def _parse_session_id(choice: str, rows: Sequence[SessionInfo]) -> str | None:
    text = choice.strip()
    if not text:
        return None
    if text.isdigit():
        index = int(text)
        if 1 <= index <= len(rows):
            return rows[index - 1].session_id
        return None
    for row in rows:
        if row.session_id == text:
            return row.session_id
    return None


def render_session_list(rows: Sequence[SessionInfo]) -> str:
    lines = [f"会话列表（共 {len(rows)} 个）"]
    for idx, row in enumerate(rows, 1):
        flag = " （当前）" if row.is_active else ""
        lines.append(f"{idx}. {row.topic}{flag} | ID: {row.session_id}")
    return "\n".join(lines)


def render_session_info(info: dict[str, Any]) -> str:
    created_at = info["created_at"].strftime("%Y-%m-%d %H:%M:%S")
    messages = info["messages"]
    tokens = info["tokens"]
    return "\n".join(
        [
            "会话信息",
            f"ID: {info['session_id']}",
            f"话题: {info['topic']}",
            f"创建时间: {created_at}",
            f"模型: {info['model']}",
            (
                "Messages: "
                f"user={messages['user']} | "
                f"assistant={messages['assistant']} | "
                f"tool calls={messages['tool_calls']} | "
                f"tool results={messages['tool_results']} | "
                f"total={messages['total']}"
            ),
            (
                "Tokens: "
                f"input={tokens['input']} | "
                f"output={tokens['output']} | "
                f"cache read={tokens['cache_read']} | "
                f"total={tokens['total']}"
            ),
            f"Cost: ${info['cost_usd']:.6f}",
        ]
    )


def resolve_model_config(
    model_name: str | None,
    channel: str = "$default",
) -> ScopedModel:
    if model_name is None:
        return get_model_config(None, channel)

    configured = next(
        (
            model
            for model in _conf.models
            if not model.hide
            and (model.name == model_name or model.alias == model_name)
        ),
        None,
    )
    if configured is None:
        raise ModelNotFoundError(f"未找到模型: {model_name}")
    return get_model_config(configured.name, channel)


def render_model_list(
    current_model: str | None = None,
    channel: str = "$default",
) -> str:
    default_model = get_default_model(channel)
    models = [model for model in _conf.models if not model.hide]
    lines = [f"模型列表（共 {len(models)} 个）"]
    for model in models:
        alias = f" ({model.alias})" if model.alias else ""
        line = f"- {model.name}{alias}"
        flags: list[str] = []
        if current_model in (model.name, model.alias):
            flags.append("当前")
        if default_model in (model.name, model.alias):
            flags.append("默认")
        if flags:
            line += " " + " ".join(f"({flag})" for flag in flags)
        lines.append(line)
    return "\n".join(lines)


def render_memory_list(rows: Sequence[UserMemory]) -> str:
    if not rows:
        return "暂无记忆"

    lines = [f"记忆列表（共 {len(rows)} 条）"]
    for index, row in enumerate(rows, 1):
        topics = f"「{', '.join(row.topics)}」" if row.topics else ""
        lines.append(f"{index}. {row.memory}{topics}")
    return "\n".join(lines)


async def select_session(session: UserSession) -> str | None:
    rows = await LLMSessionManager.list_sessions(session.user_id)
    if not rows:
        await session.send("暂无会话")
        return None

    prompt_text = f"{render_session_list(rows)}\n请输入会话序号或ID："
    resp = await session.internal.prompt(prompt_text)
    if resp is None:
        await session.send("等待超时")
        return None

    selected = _parse_session_id(resp.extract_plain_text(), rows)
    if selected is None:
        await session.send("输入无效，请输入会话序号或ID")
        return None
    return selected
