from typing import Any

from arclet.entari import BasicConfModel, plugin_config
from arclet.entari.config import model_field

from .log import logger
from ._jsondata import get_default_model
from .exception import ModelNotFoundError

_AGNO_TOOL_PREFIX = "agno.tools."


class ScopedModel(BasicConfModel):
    name: str
    """用于 OpenAI API 的模型"""
    alias: str | None = None
    """模型的别名"""
    api_key: str | None = None
    """用于使用 OpenAI API 进行身份验证的 API 密钥。如果未设置，则回退到全局 api_key"""
    base_url: str = "https://api.openai.com/v1"
    """OpenAI API 的接口地址。如果未设置，则回退到全局 base_url"""
    prompt: str = ""
    """该模型使用的提示词。如果未设置，则回退到全局 prompt"""
    hide: bool = False
    """是否在模型列表中隐藏"""
    extra: dict[str, Any] = model_field(default_factory=dict)
    """传递给 LLM API 调用的额外参数"""


class Config(BasicConfModel):
    api_key: str | None = None
    """
    用于使用 OpenAI API 进行身份验证的全局 API 密钥。
    用作没有特定 API Key 的模型的后备
    """
    base_url: str = "https://api.openai.com/v1"
    """OpenAI API 的全局接口地址。用作没有特定接口地址的模型的后备"""
    system: str = ""
    """始终应用于所有模型和调用的全局系统提示词，不会被其它 prompt 替代"""
    prompt: str = ""
    """全局提示词。用作没有特定提示词的模型的后备"""
    enable_direct_message: bool = False
    """是否允许在私聊中直接对话"""
    models: list[ScopedModel] = model_field(default_factory=list)
    """配置模型及其各自设置的列表"""
    tools: dict[str, dict[str, Any]] = model_field(default_factory=dict)
    """Entari 工具插件与 Agno Toolkit"""

    __required__ = "api_key"

    def _reload_tools(self):
        loaded_tools: dict[str, dict[str, Any]] = {}

        for key, value in self.tools.items():
            if key.startswith("$"):
                loaded_tools[key] = value
                continue

            tool_config = dict(value)
            new_key = key

            if key.startswith("~"):
                new_key = key[1:]
                if "$disable" not in tool_config or isinstance(
                    tool_config["$disable"], bool
                ):
                    tool_config["$disable"] = True
            elif key.startswith("?"):
                new_key = key[1:]
                tool_config["$optional"] = True

            if key.startswith("::agno.tools."):
                new_key = key[2:]
            elif key.startswith("::"):
                new_key = new_key.replace("::", "miraita.providers.llm.tools.builtins.")

            if tool_config.get("$disable") is True:
                continue

            loaded_tools[new_key] = tool_config

        self.tools = loaded_tools

    @property
    def agno_tools(self) -> dict[str, dict[str, Any]]:
        return {
            key: value
            for key, value in self.tools.items()
            if key.startswith(_AGNO_TOOL_PREFIX)
        }

    @property
    def entari_tools(self) -> dict[str, dict[str, Any]]:
        return {
            key: value
            for key, value in self.tools.items()
            if not key.startswith(_AGNO_TOOL_PREFIX)
        }

    def __post_init__(self):
        self._reload_tools()


_conf = plugin_config(Config)


def get_model_id(model: ScopedModel) -> str:
    return model.alias or model.name


def get_model_config(
    model_name: str | None = None, channel: str = "$default"
) -> ScopedModel:
    if model_name is None:
        if not _conf.models:
            raise ModelNotFoundError("No models configured.")

        model_name = get_default_model(channel)
        model = next(
            (m for m in _conf.models if m.name == model_name or m.alias == model_name),
            None,
        )
    else:
        model = next(
            (m for m in _conf.models if m.name == model_name or m.alias == model_name),
            None,
        )
        if not model:
            logger.warning(
                f"Model {model_name} not found in config. Using default model instead."
            )
            model_name = get_default_model(channel)
            model = next(
                (
                    m
                    for m in _conf.models
                    if m.name == model_name or m.alias == model_name
                ),
                None,
            )

    if model:
        model_cp = ScopedModel(
            name=model.name,
            alias=model.alias,
            api_key=model.api_key,
            base_url=model.base_url,
            prompt=model.prompt,
            extra=model.extra,
        )
        if not model.api_key and _conf.api_key:
            model_cp.api_key = _conf.api_key
        if (
            model.base_url == "https://api.openai.com/v1"
            and _conf.base_url != "https://api.openai.com/v1"
        ):
            model_cp.base_url = _conf.base_url
        if not model.prompt and _conf.prompt:
            model_cp.prompt = _conf.prompt
        return model_cp
    raise ModelNotFoundError(f"Model {model_name} not found in config.")


def get_model_list() -> set[str]:
    return {get_model_id(m) for m in _conf.models if not m.hide}
