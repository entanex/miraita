from typing import Literal, TypeAlias
from urllib.parse import parse_qs

from sqlalchemy import select
from arclet.entari import Entari
from entari_plugin_database import get_session as get_db_session

from ..config import config
from ..exception import BindUserException, UserUnboundException
from ..models import User
from ..schemas import Stats, StatsBar, Users

TimeScope: TypeAlias = Literal[
    "last_7_days", "last_30_days", "last_6_months", "last_year", "all_time"
]


def _get_http_client():
    app = Entari.current()
    return app.http


class API:
    _access_token_cache: dict[int, str] = {}

    @classmethod
    async def get_access_token(cls, user_id: int) -> str:
        if user_id in cls._access_token_cache:
            return cls._access_token_cache[user_id]

        async with get_db_session() as db_session:
            stmt = select(User).where(User.id == user_id)
            user = await db_session.scalar(stmt)
            if user is None:
                raise UserUnboundException

            cls._access_token_cache[user_id] = user.access_token
            return user.access_token

    @classmethod
    async def bind_user(cls, code: str) -> str:
        client = _get_http_client()
        resp = await client.post(
            "https://wakatime.com/oauth/token",
            data={
                "client_id": config.client_id,
                "client_secret": config.client_secret,
                "redirect_uri": config.redirect_uri,
                "grant_type": "authorization_code",
                "code": code,
            },
        )
        if resp.status != 200:
            raise BindUserException(f"bind failed: {resp.status} {resp.text}")

        parsed_data = parse_qs(await resp.text())
        try:
            return parsed_data["access_token"][0]
        except (KeyError, IndexError) as exc:
            raise BindUserException("bind failed: access_token not found") from exc

    @classmethod
    async def revoke_user_token(cls, user_id: int) -> int:
        access_token = await cls.get_access_token(user_id)
        client = _get_http_client()
        response = await client.post(
            "https://wakatime.com/oauth/revoke",
            data={
                "client_id": config.client_id,
                "client_secret": config.client_secret,
                "token": access_token,
            },
        )
        cls._access_token_cache.pop(user_id, None)
        return response.status

    @classmethod
    async def get_user_info(cls, user_id: int) -> Users:
        access_token = await cls.get_access_token(user_id)
        client = _get_http_client()
        response = await client.get(
            f"{config.api_url}/users/current",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        return Users(**((await response.json())["data"]))

    @classmethod
    async def get_user_stats(
        cls, user_id: int, scope: TimeScope = "last_7_days"
    ) -> Stats:
        access_token = await cls.get_access_token(user_id)
        client = _get_http_client()
        response = await client.get(
            f"{config.api_url}/users/current/stats/{scope}",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        return Stats(**((await response.json())["data"]))

    @classmethod
    async def get_user_stats_bar(cls, user_id: int) -> StatsBar | None:
        access_token = await cls.get_access_token(user_id)
        client = _get_http_client()
        response = await client.get(
            f"{config.api_url}/users/current/status_bar/today",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        data = (await response.json()).get("data")
        if not data:
            return None
        return StatsBar(**data)

    @classmethod
    async def get_all_time_since_today(cls, user_id: int) -> str:
        access_token = await cls.get_access_token(user_id)
        client = _get_http_client()
        response = await client.get(
            f"{config.api_url}/users/current/all_time_since_today",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        data = (await response.json())["data"]
        return str(data["text"])
