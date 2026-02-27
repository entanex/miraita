from pathlib import Path
from typing import Literal

from arclet.entari import BasicConfModel, plugin_config

from miraita.configs.path import IMAGE_DIR, RESOURCE_DIR, TEMPLATE_DIR


class Config(BasicConfModel):
    client_id: str = ""
    client_secret: str = ""
    redirect_uri: str = "https://wakatime.com/oauth/test"
    register_route: str = "/wakatime/register"
    api_url: str = "https://wakatime.com/api/v1"
    background_source: Literal["default", "LoliAPI", "Lolicon"] = "default"


config = plugin_config(Config)

WAKATIME_RESOURCE_DIR: Path = RESOURCE_DIR / "wakatime"
WAKATIME_TEMPLATE_DIR: Path = TEMPLATE_DIR / "wakatime"
WAKATIME_IMAGE_DIR: Path = IMAGE_DIR / "wakatime"
