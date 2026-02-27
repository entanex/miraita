from datetime import datetime
from pathlib import Path

from entari_plugin_browser import PageOption, template2html, template2img

from .config import WAKATIME_TEMPLATE_DIR
from .schemas import WakaTime
from .utils import calc_work_time_percentage, image_to_base64


async def render_wakatime(data: WakaTime) -> bytes:
    data["user"]["created_at"] = datetime.strptime(
        data["user"]["created_at"], "%Y-%m-%dT%H:%M:%SZ"
    ).strftime("%Y-%m-%d")

    return await template2img(
        template_path=str(WAKATIME_TEMPLATE_DIR),
        template_name="profile.html.jinja2",
        templates={
            "user": data["user"],
            "background_image": (
                image_to_base64(image)
                if isinstance(image := data["background_image"], Path)
                else image
            ),
            "stats_bar": data["stats_bar"],
            "insights": {
                "data": data["stats"],
                "last_week": calc_work_time_percentage(
                    data["stats"]["human_readable_total"]
                ),
                "daily_average": calc_work_time_percentage(
                    data["stats"]["human_readable_daily_average"], duration="day"
                ),
            },
            "operating_systems": data["stats"]["operating_systems"],
            "editors": data["stats"]["editors"],
            "languages": data["stats"]["languages"],
            "all_time_since_today": data["all_time_since_today"],
        },
        page_option=PageOption(
            viewport={"width": 550, "height": 10},
            base_url=WAKATIME_TEMPLATE_DIR.as_uri(),
        ),
    )


async def render_bind_result(status_code: int, content: str) -> str:
    result = "success" if status_code == 200 else "error"
    return await template2html(
        template_path=str(WAKATIME_TEMPLATE_DIR),
        template_name=f"{result}.html.jinja2",
        status_code=status_code,
        content=content,
    )
