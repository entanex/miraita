from pathlib import Path
from arclet.entari.localdata import local_data

BOT_DIR = Path.cwd()
"""机器人根目录"""

APP_NAME = local_data.base_dir or f".{local_data.app_name.lstrip('.')}"


DATA_DIR = BOT_DIR / APP_NAME / "data"
"""数据保存目录"""
RESOURCE_DIR = BOT_DIR / APP_NAME / "resources"
"""资源保存目录"""

IMAGE_DIR = RESOURCE_DIR / "images"
"""图片保存目录"""
FONT_DIR = RESOURCE_DIR / "fonts"
"""字体保存目录"""
STICKER_DIR = RESOURCE_DIR / "stickers"
"""表情包保存目录"""
TEMPLATE_DIR = RESOURCE_DIR / "templates"
"""模板保存目录"""

for name, var in locals().copy().items():
    if name.endswith("_DIR") and isinstance(var, Path):
        var.mkdir(parents=True, exist_ok=True)
