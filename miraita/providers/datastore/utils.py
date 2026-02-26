import inspect

from arclet.entari.plugin import find_plugin


_INTERNAL_MODULE_PREFIXES = ("miraita.providers.datastore",)


def get_caller_plugin_name() -> str:
    frame = inspect.currentframe()
    if frame is None:
        raise ValueError("无法获取当前栈帧")

    while frame := frame.f_back:
        module_name = frame.f_globals.get("__name__")
        if not module_name:
            module_name = (module := inspect.getmodule(frame)) and module.__name__
        if not module_name:
            continue

        if module_name.startswith(_INTERNAL_MODULE_PREFIXES):
            continue

        if plugin := find_plugin(module_name):
            return plugin.id.split(".")[2]

    raise ValueError("自动获取插件名失败")
