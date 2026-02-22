from collections.abc import Sequence

from arclet.entari import Session

from .manager import LLMSessionManager
from .._jsondata import get_default_model
from ..config import _conf
from ..model import LLMSession


def _parse_session_id(choice: str, rows: Sequence[LLMSession]) -> str | None:
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


def render_session_list(rows: Sequence[LLMSession]) -> str:
    lines = [f"会话列表（共 {len(rows)} 个）"]
    for idx, row in enumerate(rows, 1):
        flag = " [当前]" if row.is_active else ""
        lines.append(f"{idx}. {row.topic}{flag} | ID: {row.session_id}")
    return "\n".join(lines)


def render_model_list() -> str:
    default_model = get_default_model()
    lines = [f"模型列表（共 {len(_conf.models)} 个）"]
    for model in _conf.models:
        alias = f" ({model.alias})" if model.alias else ""
        is_default = " [默认]" if default_model == model.name else ""
        lines.append(f"- {model.name}{alias}{is_default}")
    return "\n".join(lines)


async def select_session(session: Session) -> str | None:
    rows = await LLMSessionManager.list_sessions(session.user)
    if not rows:
        await session.send("暂无会话")
        return None

    prompt_text = f"{render_session_list(rows)}\n请输入会话序号或ID："
    resp = await session.prompt(prompt_text)
    if resp is None:
        await session.send("等待超时")
        return None

    selected = _parse_session_id(resp.extract_plain_text(), rows)
    if selected is None:
        await session.send("输入无效，请输入会话序号或ID")
        return None
    return selected
