import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from arclet.entari import local_data


@dataclass(slots=True)
class SessionPointer:
    session_id: str
    created_at: int


@dataclass(slots=True)
class LLMState:
    default_model: str | None = None
    current_sessions: dict[str, SessionPointer] = field(default_factory=dict)
    session_models: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LLMState":
        value = data.get("default_model")
        default_model = value if isinstance(value, str) and value else None

        current_sessions: dict[str, SessionPointer] = {}
        raw_sessions = data.get("current_sessions")
        if isinstance(raw_sessions, dict):
            for user_id, raw_pointer in raw_sessions.items():
                if not isinstance(user_id, str) or not isinstance(raw_pointer, dict):
                    continue
                session_id = raw_pointer.get("session_id")
                created_at = raw_pointer.get("created_at")
                if isinstance(session_id, str) and isinstance(created_at, int):
                    current_sessions[user_id] = SessionPointer(session_id, created_at)

        session_models: dict[str, str] = {}
        raw_models = data.get("session_models")
        if isinstance(raw_models, dict):
            session_models = {
                session_id: model
                for session_id, model in raw_models.items()
                if isinstance(session_id, str) and isinstance(model, str) and model
            }

        return cls(
            default_model=default_model,
            current_sessions=current_sessions,
            session_models=session_models,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _state_path() -> Path:
    return local_data.get_data_file("llm", "state.json")


def _load_data() -> dict[str, Any]:
    path = _state_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _read_state(channel: str) -> LLMState:
    data = _load_data()
    result = data.get(channel)
    if not isinstance(result, dict):
        result = data.get("$default")
    if not isinstance(result, dict) and any(
        key in data for key in ("default_model", "current_sessions", "session_models")
    ):
        result = data
    return LLMState.from_dict(result if isinstance(result, dict) else {})


def _write_state(state: LLMState, channel: str) -> None:
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _load_data()
    if any(
        key in data for key in ("default_model", "current_sessions", "session_models")
    ):
        data = {"$default": LLMState.from_dict(data).to_dict()}
    data[channel] = state.to_dict()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_default_model(channel: str = "$default") -> str | None:
    return _read_state(channel).default_model


def set_default_model(model_name: str | None, channel: str = "$default") -> None:
    state = _read_state(channel)
    state.default_model = model_name if model_name else None
    _write_state(state, channel)


def get_current_session(user_id: str | int) -> SessionPointer | None:
    return _read_state("$default").current_sessions.get(str(user_id))


def set_current_session(user_id: str | int, session_id: str, created_at: int) -> None:
    user_id = str(user_id)
    state = _read_state("$default")
    state.current_sessions[user_id] = SessionPointer(session_id, created_at)
    _write_state(state, "$default")


def clear_current_session(user_id: str | int) -> None:
    user_id = str(user_id)
    state = _read_state("$default")
    if state.current_sessions.pop(user_id, None) is not None:
        _write_state(state, "$default")


def get_session_model(session_id: str) -> str | None:
    return _read_state("$default").session_models.get(session_id)


def set_session_model(session_id: str, model: str) -> None:
    state = _read_state("$default")
    state.session_models[session_id] = model
    _write_state(state, "$default")


def clear_session_model(session_id: str) -> None:
    state = _read_state("$default")
    if state.session_models.pop(session_id, None) is not None:
        _write_state(state, "$default")
