import base64
import re
from pathlib import Path
from typing import Literal

from arclet.entari import Entari

from .config import (
    WAKATIME_IMAGE_DIR,
    config,
)


def image_to_base64(image_path: Path) -> str:
    with image_path.open("rb") as image_file:
        base64_encoded_data = base64.b64encode(image_file.read())
    return "data:image/png;base64," + base64_encoded_data.decode("utf-8")


async def get_lolicon_image() -> str:
    app = Entari.current()
    response = await app.http.get("https://api.lolicon.app/setu/v2")
    response.raise_for_status()
    return (await response.json())["data"][0]["urls"]["original"]


async def get_background_image() -> str | Path:
    default_background = WAKATIME_IMAGE_DIR / "background.png"

    if config.background_source == "default":
        return default_background
    if config.background_source == "LoliAPI":
        return "https://www.loliapi.com/acg/pe/"
    if config.background_source == "Lolicon":
        return await get_lolicon_image()
    return default_background


def parse_time(work_time: str) -> int:
    patterns = {
        "hrs": r"(\d+)\s*hrs?",
        "mins": r"(\d+)\s*mins?",
        "secs": r"(\d+)\s*secs?",
    }

    hours = minutes = seconds = 0
    for key, pattern in patterns.items():
        match = re.search(pattern, work_time)
        if not match:
            continue
        if key == "hrs":
            hours = int(match.group(1))
        elif key == "mins":
            minutes = int(match.group(1))
        else:
            seconds = int(match.group(1))

    return hours * 3600 + minutes * 60 + seconds


def calc_work_time_percentage(
    work_time: str, *, duration: Literal["day", "week", "month"] = "week"
) -> float:
    if duration == "day":
        total_minutes = 24 * 60
    elif duration == "week":
        total_minutes = 7 * 24 * 60
    else:
        total_minutes = 30 * 24 * 60

    total_work_minutes = parse_time(work_time) / 60
    return (total_work_minutes / total_minutes) * 100
