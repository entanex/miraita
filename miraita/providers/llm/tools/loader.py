from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from importlib import import_module
from typing import Any

from agno.tools import Toolkit

from ..log import logger
from .limit import (
    CALL_LIMIT_OPTION,
    apply_function_call_limit,
    get_call_limit,
)


@dataclass(frozen=True, slots=True)
class AgnoToolSpec:
    path: str
    toolkit_type: type[Toolkit]
    options: dict[str, Any]
    call_limit: int | None = None

    def build(self) -> Toolkit:
        try:
            toolkit = self.toolkit_type(**self.options)
            if self.call_limit is not None:
                apply_function_call_limit(
                    (*toolkit.functions.values(), *toolkit.async_functions.values()),
                    self.path,
                    self.call_limit,
                )
            return toolkit
        except Exception as exc:
            raise RuntimeError(f"初始化 Agno 工具 {self.path!r} 失败: {exc}") from exc


def resolve_agno_tool_specs(
    configs: Mapping[str, Mapping[str, Any]] | None,
) -> tuple[AgnoToolSpec, ...]:
    """Resolve configured Agno Toolkit classes without sharing runtime instances."""
    if configs is None:
        return ()
    if not isinstance(configs, Mapping):
        raise TypeError("agno_tools 必须是工具类路径到构造参数的映射")

    specs: list[AgnoToolSpec] = []
    for path, options in configs.items():
        if not isinstance(path, str) or not path.startswith("agno.tools."):
            raise ValueError(f"Agno 工具必须使用 agno.tools 下的完整类路径: {path!r}")
        if not isinstance(options, Mapping):
            raise TypeError(f"Agno 工具 {path!r} 的配置必须是映射")

        module_name, separator, attribute = path.rpartition(".")
        if not separator or not attribute:
            raise ValueError(f"无效的 Agno 工具类路径: {path!r}")

        try:
            module = import_module(module_name)
        except ImportError as exc:
            raise ImportError(f"导入 Agno 工具 {path!r} 失败: {exc}") from exc

        try:
            toolkit_type = getattr(module, attribute)
        except AttributeError as exc:
            raise ImportError(f"Agno 工具 {path!r} 不存在") from exc

        if (
            not isinstance(toolkit_type, type)
            or not issubclass(toolkit_type, Toolkit)
            or toolkit_type is Toolkit
        ):
            raise TypeError(f"{path!r} 不是 Agno Toolkit 子类")

        tool_options = dict(options)
        call_limit = get_call_limit(path, tool_options)
        tool_options.pop(CALL_LIMIT_OPTION, None)

        specs.append(AgnoToolSpec(path, toolkit_type, tool_options, call_limit))
        logger.debug(f"Registered tool: {toolkit_type.__name__}")

    return tuple(specs)


def build_agno_tools(specs: Iterable[AgnoToolSpec]) -> list[Toolkit]:
    """Build request-scoped Toolkit instances from resolved configuration."""
    return [spec.build() for spec in specs]
