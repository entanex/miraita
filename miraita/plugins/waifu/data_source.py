import json
from dataclasses import dataclass, asdict

from arclet.entari import local_data


@dataclass
class WaifuJsonData:
    user_id: str
    waifu_id: str


async def get_waifu_data(user_id: str) -> WaifuJsonData | None:
    file = local_data.get_data_file("waifu", "data.json")

    try:
        with open(file, encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

    if user_id not in data:
        return None

    user_data = data[user_id]
    return WaifuJsonData(**user_data)


async def save_waifu_data(user_id: str, waifu_id: str) -> None:
    file = local_data.get_data_file("waifu", "data.json")

    try:
        with open(file) as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}

    data[user_id] = asdict(WaifuJsonData(user_id=user_id, waifu_id=waifu_id))

    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


async def clear_waifu_data() -> None:
    file = local_data.get_data_file("waifu", "data.json")
    with open(file, "w", encoding="utf-8") as f:
        json.dump({}, f, ensure_ascii=False, indent=2)
