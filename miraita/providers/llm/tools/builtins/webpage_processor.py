from arclet.entari import plugin
from entari_plugin_browser import playwright_api, _config

from miraita.providers.llm.log import logger

from ..event import LLMToolEvent

tools = plugin.dispatch(LLMToolEvent)


async def get_browser():
    if _config.browser_type == "chromium":
        return await playwright_api.playwright.chromium.launch()
    elif _config.browser_type == "firefox":
        return await playwright_api.playwright.firefox.launch()
    elif _config.browser_type == "webkit":
        return await playwright_api.playwright.webkit.launch()
    else:
        raise ValueError(f"Unsupported browser type: {_config.browser_type}")


@tools
async def process_web_page(url: str) -> str | None:
    """处理网页内容

    Args:
        url: 网页 URL

    Returns:
        Optional[str]: 网页内容, 失败时返回None
    """

    try:
        browser = await get_browser()
        page = await browser.new_page()

        try:
            await page.goto(url, timeout=60000)
        except Exception as e:
            logger.opt(exception=e).error(f"打开链接失败: {url}, 错误: {e}")
            await page.close()
            return None

        page_content = await page.query_selector("html")
        content_text = None

        if page_content:
            content_text = await page_content.inner_text()

        await page.close()

    except Exception as e:
        logger.opt(exception=e).error(f"处理网页失败: {url}, 错误: {e}")
        return None
    else:
        return content_text
