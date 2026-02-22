from arclet.entari import declare_static, metadata

from .config import Config
from .events import LLMToolEvent as LLMToolEvent
from .log import _suppress_litellm_logging

metadata(
    name="LLM",
    author=[
        {"name": "RF-Tar-Railt", "email": "rf_tar_railt@qq.com"},
        {"name": "Komorebi", "email": "mute231010@gmail.com"},
    ],
    description="LLM Chat",
    classifier=["AI", "工具"],
    config=Config,
)
declare_static()
_suppress_litellm_logging()

from .handlers import chat as chat  # entari: plugin
from .handlers import check as check  # entari: plugin
from .handlers import command as command  # entari: plugin
from .service import llm as llm

__all__ = [
    "llm",
    "LLMToolEvent",
]
