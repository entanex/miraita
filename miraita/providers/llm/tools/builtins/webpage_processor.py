from launart import Launart
from entari_plugin_browser import PlaywrightService

from miraita.providers.llm.log import logger

from ..event import llm_tool


@llm_tool
async def process_web_page(url: str) -> str | None:
    """处理 HTML 网页内容；文件链接应使用 read_file，不要使用本工具。

    Args:
        url: HTML 网页 URL，不用于 PDF、Word、TXT 或 Markdown 文件。

    Returns:
        Optional[str]: 网页内容, 失败时返回 None
    """
    try:
        manager = Launart.current()
        pw_service = manager.get_component(PlaywrightService)
    except (LookupError, ValueError, RuntimeError):
        logger.error("PlaywrightService 未找到，无法处理网页内容")
        return None

    content_text = None
    async with pw_service.page() as page:
        try:
            await page.goto(url, timeout=60000)
        except Exception as e:
            logger.opt(exception=e).error(f"打开链接失败: {url}, 错误: {e}")
            return None

        if page_content := await page.query_selector("html"):
            content_text = await page_content.inner_text()

    return content_text
