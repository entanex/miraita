from arclet.entari.event.lifespan import Ready
from arclet.letoderea import on

from .log import logger
from .config import _conf
from ._jsondata import get_default_model, set_default_model


@on(Ready)
async def check():
    if not _conf.models:
        set_default_model(None)
        logger.warning("未配置任何模型，已清空本地默认模型配置")
        return

    first_model = _conf.models[0].name
    default_model = get_default_model()
    if not default_model:
        set_default_model(first_model)
        logger.info(f"未检测到本地默认模型，已设置为首个模型: {first_model}")
        return

    matched = next(
        (
            m
            for m in _conf.models
            if m.name == default_model or m.alias == default_model
        ),
        None,
    )
    if matched is None:
        set_default_model(first_model)
        logger.warning(
            f"本地默认模型不存在于当前配置: {default_model}，已重置为: {first_model}",
        )
        return

    if matched.name != default_model:
        set_default_model(matched.name)
        logger.info(f"已将本地默认模型标准化为模型名: {matched.name}")
