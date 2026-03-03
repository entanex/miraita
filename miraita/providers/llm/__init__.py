from arclet.entari import metadata

from .config import Config
from .events import LLMToolEvent as LLMToolEvent
from .log import _suppress_litellm_logging
from . import listener as listener

metadata(
    name="LLM Toolkit",
    author=[
        {"name": "RF-Tar-Railt", "email": "rf_tar_railt@qq.com"},
        {"name": "Komorebi", "email": "mute231010@gmail.com"},
    ],
    description="LLM 工具",
    classifier=["服务"],
    config=Config,
)
_suppress_litellm_logging()

from .service import llm as llm

__all__ = [
    "llm",
    "LLMToolEvent",
]
