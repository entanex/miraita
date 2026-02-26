from arclet.entari.logger import log as log_m

logger = log_m.wrapper("[llm]")


def log(level: str, rich_text: str) -> None:
    getattr(logger.opt(colors=True), level)(
        rich_text.replace("[", "<").replace("]", ">"),
        alt=rich_text,
    )


def _suppress_litellm_logging() -> None:
    """Configure logging to suppress LiteLLM info and debug logs.

    See https://github.com/BerriAI/litellm/issues/6813
    """
    import logging

    logging.getLogger("LiteLLM").setLevel(logging.WARNING)
