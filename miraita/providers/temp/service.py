from __future__ import annotations

from typing import Any
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
import mimetypes
from contextlib import asynccontextmanager
from dataclasses import dataclass
from urllib.parse import unquote, urlsplit
from collections.abc import AsyncIterator

from launart import Launart, Service
from arclet.entari import Entari, Account, add_service
from launart.status import Phase

_DOWNLOAD_CHUNK_SIZE = 1024 * 1024
_DEFAULT_MAX_FILE_SIZE = 50 * 1024 * 1024
_DEFAULT_TIMEOUT_SECONDS = 60


@dataclass(frozen=True, slots=True)
class DownloadedFile:
    path: Path
    content_type: str | None
    charset: str | None
    filename: str | None


def _suffix_from_candidate(value: str | None) -> str:
    if not value:
        return ""
    candidate = unquote(urlsplit(value).path)
    suffix = (
        candidate.lower()
        if candidate.startswith(".")
        else Path(candidate).suffix.lower()
    )
    if not suffix or len(suffix) > 16 or not suffix[1:].isalnum():
        return ""
    return suffix


def _resolve_suffix(
    source_url: str,
    response_url: str,
    response_filename: str | None,
    content_type: str | None,
    filename: str | None,
) -> str:
    for candidate in (filename, response_filename, response_url, source_url):
        if suffix := _suffix_from_candidate(candidate):
            return suffix

    if content_type and content_type.lower() != "application/octet-stream":
        return _suffix_from_candidate(
            mimetypes.guess_extension(content_type.lower(), strict=False)
        )
    return ""


class TempFileService(Service):
    id = "miraita/temp"

    def __init__(self) -> None:
        super().__init__()
        self._directory: TemporaryDirectory[str] | None = None

    @property
    def required(self) -> set[str]:
        return set()

    @property
    def stages(self) -> set[Phase]:
        return {"preparing", "blocking", "cleanup"}

    @property
    def root(self) -> Path:
        if self._directory is None:
            self._directory = TemporaryDirectory(prefix="miraita-")
        return Path(self._directory.name)

    def cleanup(self) -> None:
        directory = self._directory
        self._directory = None
        if directory is not None:
            directory.cleanup()

    @staticmethod
    def _find_internal_account(app: Entari, url: str) -> Account:
        target = url.split(":", 1)[1]
        try:
            platform, self_id, _ = target.split("/", 2)
        except ValueError as exc:
            raise ValueError(f"无效的内部文件链接: {url}") from exc

        for account in app.accounts.values():
            if account.platform == platform and account.self_id == self_id:
                return account
        raise ValueError(f"未找到内部文件链接对应的账号: {platform}:{self_id}")

    @classmethod
    def _resolve_url(
        cls,
        app: Entari,
        url: str,
        account: Account | None,
    ) -> Any:
        scheme = urlsplit(url).scheme.lower()
        if scheme not in {"http", "https", "internal"}:
            raise ValueError("临时文件仅支持 HTTP、HTTPS 或内部链接")
        if account is not None:
            return account.ensure_url(url)
        if scheme == "internal":
            return cls._find_internal_account(app, url).ensure_url(url)
        return url

    @asynccontextmanager
    async def download(
        self,
        url: str,
        *,
        app: Entari | None = None,
        account: Account | None = None,
        filename: str | None = None,
        max_size: int | None = _DEFAULT_MAX_FILE_SIZE,
        timeout: float = _DEFAULT_TIMEOUT_SECONDS,
    ) -> AsyncIterator[DownloadedFile]:
        current_app = app or Entari.current()
        request_url = self._resolve_url(current_app, url, account)
        path: Path | None = None

        try:
            async with current_app.http.get(
                request_url,
                allow_redirects=True,
                timeout=timeout,
            ) as response:
                response.raise_for_status()
                content_disposition = response.content_disposition
                response_filename = (
                    content_disposition.filename if content_disposition else None
                )
                content_type = response.content_type or None
                suffix = _resolve_suffix(
                    url,
                    str(response.url),
                    response_filename,
                    content_type,
                    filename,
                )

                if (
                    max_size is not None
                    and response.content_length is not None
                    and response.content_length > max_size
                ):
                    raise ValueError("文件大小超过临时文件限制")

                downloaded = 0
                with NamedTemporaryFile(
                    mode="wb",
                    prefix="download-",
                    suffix=suffix,
                    dir=self.root,
                    delete=False,
                ) as output:
                    path = Path(output.name)
                    async for chunk in response.content.iter_chunked(
                        _DOWNLOAD_CHUNK_SIZE
                    ):
                        downloaded += len(chunk)
                        if max_size is not None and downloaded > max_size:
                            raise ValueError("文件大小超过临时文件限制")
                        output.write(chunk)

                temporary_file = DownloadedFile(
                    path=path,
                    content_type=content_type,
                    charset=response.charset,
                    filename=filename or response_filename,
                )

            yield temporary_file
        finally:
            if path is not None:
                path.unlink(missing_ok=True)

    async def launch(self, manager: Launart) -> None:
        async with self.stage("preparing"):
            self.root

        async with self.stage("blocking"):
            await manager.status.wait_for_sigexit()

        async with self.stage("cleanup"):
            self.cleanup()


temp = TempFileService()
add_service(temp)
