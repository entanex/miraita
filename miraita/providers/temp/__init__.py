from arclet.entari import metadata

from .service import DownloadedFile as DownloadedFile
from .service import TempFileService as TempFileService
from .service import temp as temp

metadata(
    name="临时文件服务",
    author=[{"name": "Komorebi", "email": "mute231010@gmail.com"}],
    description="为 Miraita 提供请求级临时文件下载与清理",
    classifier=["服务"],
)

__all__ = ["DownloadedFile", "TempFileService", "temp"]
