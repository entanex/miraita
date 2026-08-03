import os

from arclet.entari import metadata, plugin
from arclet.entari.plugin import PluginRole

from .config import Config, _conf
from .response import GenericResponse as GenericResponse
from .config import get_model_config as get_model_config
from .tools import LLMToolEvent as LLMToolEvent
from .log import _suppress_litellm_logging
from . import listener as listener

metadata(
    name="LLM 工具箱",
    role=PluginRole.COMPLEX,
    author=[
        {"name": "RF-Tar-Railt", "email": "rf_tar_railt@qq.com"},
        {"name": "Komorebi", "email": "mute231010@gmail.com"},
    ],
    description="LLM 工具",
    classifier=["服务"],
    config=Config,
)
_suppress_litellm_logging()
os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")


for tool in _conf.entari_tools:
    plugin.load_plugin(tool)

from .service import llm as llm
