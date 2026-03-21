from __future__ import annotations

import io
import re
import shutil
import zipfile
from hashlib import sha256
from pathlib import Path

from launart import Launart
from arclet.entari import Startup, Entari
from arclet.letoderea import on

from miraita import logger
from miraita.configs import RESOURCE_DIR

REMOTE_ZIP_URL = "https://raw.githubusercontent.com/entanex/miraita-resources/master/miraita-resources.zip"
VERSION_FILE = "__version__"


def _read_local_version() -> str:
    version_path = RESOURCE_DIR / VERSION_FILE
    if not version_path.is_file():
        return ""
    return version_path.read_text(encoding="utf-8").strip()


def _parse_version(version: str) -> tuple[int, ...] | None:
    cleaned = version.strip().lstrip("vV")
    if not cleaned:
        return None
    if not re.match(r"^\d+(?:\.\d+)*$", cleaned):
        return None
    return tuple(int(part) for part in cleaned.split("."))


def _is_lower_version(local: str, remote: str) -> bool:
    local_v = _parse_version(local)
    remote_v = _parse_version(remote)
    if local_v is None or remote_v is None:
        return local != remote
    length = max(len(local_v), len(remote_v))
    local_v = local_v + (0,) * (length - len(local_v))
    remote_v = remote_v + (0,) * (length - len(remote_v))
    return local_v < remote_v


def _read_remote_version_from_zip(zf: zipfile.ZipFile) -> str:
    candidates = [name for name in zf.namelist() if name.endswith(VERSION_FILE)]
    if not candidates:
        return ""
    version_file = min(candidates, key=lambda x: x.count("/"))
    content = zf.read(version_file).decode("utf-8", errors="ignore").strip()
    return content


def _safe_extract(zf: zipfile.ZipFile, target_dir: Path) -> None:
    target_dir = target_dir.resolve()
    for member in zf.infolist():
        member_path = (target_dir / member.filename).resolve()
        if not str(member_path).startswith(str(target_dir)):
            raise RuntimeError(f"Illegal archive path: {member.filename}")
    zf.extractall(target_dir)


@on(Startup)
async def check_resources(app: Entari, launart: Launart):
    try:
        is_empty = not any(RESOURCE_DIR.iterdir())
        local_version = _read_local_version()

        response = await app.http.get(REMOTE_ZIP_URL)
        response.raise_for_status()
        zip_bytes = await response.read()

        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            remote_version = _read_remote_version_from_zip(zf)

        if not remote_version:
            remote_version = f"sha256:{sha256(zip_bytes).hexdigest()}"

        need_update = (
            is_empty
            or not local_version
            or _is_lower_version(local_version, remote_version)
        )
        if not need_update:
            return

        logger.info(
            "检测到资源需要更新，开始下载并解压。"
            f"{local_version or 'N/A'} -> {remote_version}"
        )

        if RESOURCE_DIR.exists():
            shutil.rmtree(RESOURCE_DIR)
        RESOURCE_DIR.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            _safe_extract(zf, RESOURCE_DIR)

        (RESOURCE_DIR / VERSION_FILE).write_text(remote_version, encoding="utf-8")
        logger.success("资源下载完成")
    except Exception:
        logger.exception("资源检测或下载失败")
