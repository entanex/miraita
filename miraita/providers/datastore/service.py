import json
from pathlib import Path
from typing import Any, TypeVar, overload

from launart import Service, Launart
from launart.status import Phase
from arclet.entari import add_service, local_data

from .utils import get_caller_plugin_name

T = TypeVar("T")


class DatastoreService(Service):
    id = "datastore"
    DEFAULT_STORE_FILE = "data.json"

    @property
    def required(self):
        return set()

    @property
    def stages(self) -> set[Phase]:
        return {"blocking"}

    def __init__(self):
        super().__init__()

    @property
    def data_dir(self) -> Path:
        plugin_name = get_caller_plugin_name()
        return local_data.get_data_dir(plugin_name)

    def data_file(self, filename: str) -> Path:
        plugin_name = get_caller_plugin_name()
        return local_data.get_data_file(plugin_name, filename)

    def read_json(self, filename: str, default: Any | None = None) -> Any | None:
        path = self.data_file(filename)
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return default

    def write_json(self, filename: str, data: Any, *, indent: int = 2) -> Path:
        path = self.data_file(filename)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=indent),
            encoding="utf-8",
        )
        return path

    def _read_store(self) -> dict[str, Any]:
        data = self.read_json(self.DEFAULT_STORE_FILE, default={})
        if isinstance(data, dict):
            return data
        return {}

    def _write_store(self, data: dict[str, Any]) -> None:
        self.write_json(self.DEFAULT_STORE_FILE, data)

    @overload
    def get(self, key: str) -> Any | None: ...

    @overload
    def get(self, key: str, default: T) -> T | Any: ...

    def get(self, key: str, default: Any = None) -> Any:
        return self._read_store().get(key, default)

    def set(self, key: str, value: Any) -> None:
        data = self._read_store()
        data[key] = value
        self._write_store(data)

    def set_all(self, value: Any) -> None:
        self.write_json(self.DEFAULT_STORE_FILE, value)

    def clear(self) -> None:
        self._write_store({})

    def all(self) -> dict[str, Any]:
        return self._read_store().copy()

    async def launch(self, manager: Launart):
        async with self.stage("blocking"):
            await manager.status.wait_for_sigexit()


datastore = DatastoreService()
add_service(datastore)
