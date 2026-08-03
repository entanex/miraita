from urllib.parse import urlsplit

from launart import Launart
from entari_plugin_browser import PlaywrightService

from miraita.providers.llm.log import logger

from ..event import llm_tool


def _validate_web_page_url(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        raise ValueError("网页地址必须是完整的 HTTP 或 HTTPS URL")


@llm_tool
async def process_web_page(url: str) -> str | None:
    """处理 HTML 网页内容；文件链接应使用 read_file，不要使用本工具。

    Args:
        url: HTML 网页 URL，不用于 PDF、Word、TXT 或 Markdown 文件。

    Returns:
        Optional[str]: 网页内容, 失败时返回 None
    """
    _validate_web_page_url(url)
    try:
        manager = Launart.current()
        pw_service = manager.get_component(PlaywrightService)
    except (LookupError, ValueError, RuntimeError):
        logger.error("PlaywrightService 未找到，无法处理网页内容")
        return None

    content_text = None
    async with pw_service.page() as page:
        try:
            response = await page.goto(url, timeout=60000)
        except Exception as e:
            logger.opt(exception=e).error(f"打开链接失败: {url}, 错误: {e}")
            return None
        if response is not None:
            content_type = await response.header_value("content-type")
            media_type = (content_type or "").partition(";")[0].strip().lower()
            if media_type and media_type not in {
                "text/html",
                "application/xhtml+xml",
            }:
                logger.warning(
                    f"目标资源不是 HTML 网页: {url}, Content-Type: {media_type}"
                )
                return None

        if page_content := await page.query_selector("html"):
            content_text = await page_content.inner_text()

    return content_text
