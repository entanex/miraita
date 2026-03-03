from typing import Any

from arclet.entari import BasicConfModel, plugin_config
from arclet.entari.config import model_field

from ._jsondata import get_default_model
from .exception import ModelNotFoundError


class ScopedModel(BasicConfModel):
    name: str
    """Model to use for the OpenAI API"""
    alias: str | None = None
    """Alias for the model"""
    api_key: str | None = None
    """
    API key for authentication with the OpenAI API.
    If None, falls back to global api_key
    """
    base_url: str = "https://api.openai.com/v1"
    """Base URL for the OpenAI API"""
    prompt: str = ""
    """Default prompt template"""
    extra: dict[str, Any] = model_field(default_factory=dict)
    """Extra parameters to pass to the LLM API call"""


class Config(BasicConfModel):
    api_key: str | None = None
    """
    Global API key for authentication with the OpenAI API.
    Used as fallback for models without specific keys
    """
    base_url: str = "https://api.openai.com/v1"
    """
    Global Base URL for the OpenAI API.
    Used as fallback for models without specific base URLs
    """
    prompt: str = ""
    """Default prompt template"""
    models: list[ScopedModel] = model_field(default_factory=list)
    """List of configured models with their individual settings"""

    __required__ = "api_key"


_conf = plugin_config(Config)


def get_model_config(model_name: str | None = None) -> ScopedModel:
    if model_name is None:
        if not _conf.models:
            raise ModelNotFoundError("No models configured.")

        model_name = get_default_model()

    for model in _conf.models:
        if model.name == model_name or model.alias == model_name:
            if model.api_key is None:
                model.api_key = _conf.api_key
            if (
                model.base_url == "https://api.openai.com/v1"
                and _conf.base_url != "https://api.openai.com/v1"
            ):
                model.base_url = _conf.base_url
            return model
    raise ModelNotFoundError(f"Model {model_name} not found in config.")


def get_model_list() -> set[str]:
    return {m.name for m in _conf.models} | {m.alias for m in _conf.models if m.alias}
