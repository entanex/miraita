from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import arclet.entari as entari
import arclet.entari.plugin as plugin

from arclet.entari import Plugin
from arclet.entari.plugin import PluginMetadata

_PATCHED = False


def _normalize_required(required: Any) -> tuple[str, ...]:
    if isinstance(required, str):
        return (required,)
    if isinstance(required, Iterable):
        return tuple(item for item in required if isinstance(item, str))
    return ()


def _patched_metadata(*args, **kwargs):
    plugin = Plugin.current()
    meta = PluginMetadata(*args, **kwargs)
    plugin.metadata = meta

    config_model = meta.config
    if config_model is None:
        return

    required_fields = _normalize_required(getattr(config_model, "__required__", ()))
    if not required_fields:
        return

    plugin_config = plugin.config if isinstance(plugin.config, dict) else {}
    if any(plugin_config.get(field) is None for field in required_fields):
        plugin.disable()


def patch_metadata():
    global _PATCHED
    if _PATCHED:
        return

    entari.metadata = _patched_metadata
    plugin.metadata = _patched_metadata
    _PATCHED = True
