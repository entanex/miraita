from typing_extensions import TypedDict


class Users(TypedDict):
    id: str
    photo: str
    last_project: str
    username: str
    created_at: str
