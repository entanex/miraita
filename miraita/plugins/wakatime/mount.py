from dataclasses import dataclass
from datetime import datetime, timedelta
from secrets import token_hex
from urllib.parse import urlparse

from starlette.requests import Request
from starlette.responses import HTMLResponse
from yarl import URL
from entari_plugin_database import get_session as get_db_session
from entari_plugin_server import add_route


from .apis import API
from .log import logger
from .config import config
from .models import User
from .render import render_bind_result


@dataclass
class WaitingRecord:
    user_id: int
    expired_at: datetime


waiting_codes: dict[str, WaitingRecord] = {}


def is_mountable() -> bool:
    if not config.redirect_uri:
        return False
    host = urlparse(config.redirect_uri).hostname
    if host and host.endswith("wakatime.com"):
        return False
    return True


def create_state(user_id: int) -> str:
    state = token_hex(20)
    waiting_codes[state] = WaitingRecord(
        user_id=user_id, expired_at=datetime.now() + timedelta(minutes=5)
    )
    return state


def consume_waiting_state(state: str) -> WaitingRecord | None:
    record = waiting_codes.pop(state, None)
    if record is None:
        return None
    if record.expired_at < datetime.now():
        return None
    return record


def build_authorize_url(state: str) -> URL:
    assert config.client_id

    return URL("https://wakatime.com/oauth/authorize").with_query(
        {
            "client_id": config.client_id,
            "response_type": "code",
            "redirect_uri": config.redirect_uri,
            "scope": "read_stats,read_summaries",
            "state": state,
        }
    )


if is_mountable():

    @add_route(config.register_route, methods=["GET"], include_in_schema=False)
    async def register_code_handler(request: Request):
        code = request.query_params.get("code")
        state = request.query_params.get("state")

        if code is None or state is None:
            html = await render_bind_result(400, "Bad Request.")
            return HTMLResponse(content=html, status_code=400)

        record = consume_waiting_state(state)
        if record is None:
            html = await render_bind_result(404, "User Not Found or Expired.")
            return HTMLResponse(content=html, status_code=404)

        access_token = await API.bind_user(code)
        async with get_db_session() as db_session:
            user = await db_session.get(User, record.user_id)
            if user is None:
                db_session.add(User(id=record.user_id, access_token=access_token))
            else:
                user.access_token = access_token
            await db_session.commit()

        html = await render_bind_result(200, "Bind OK.")
        return HTMLResponse(content=html, status_code=200)

    logger.success("挂载 wakatime 自动注册路由")
