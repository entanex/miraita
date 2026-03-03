from arclet.alconna import (
    Alconna,
    Args,
    CommandMeta,
    Namespace,
    command_manager,
    config,
)
from arclet.entari import metadata, command, Session, Image

from entari_plugin_browser import md2img

from miraita.utils.formatter import MarkdownTextFormatter

from .log import logger


metadata(
    name="帮助",
    author=[{"name": "Komorebi", "email": "mute231010@gmail.com"}],
    description="帮助",
    classifier=["工具"],
)

ns = Namespace("帮助")
config.namespaces["帮助"] = ns


help = Alconna(
    "help",
    Args["plugin?#插件名", str],
    meta=CommandMeta(
        description="插件帮助", usage="/help [插件名]", example="/help 谁是卷王"
    ),
    namespace=ns,
)


@command.on(help)
async def _(plugin: command.Match[str], session: Session):
    async def send_command_help(namespace: str):
        all_commands = command_manager.get_commands(namespace)
        cmds = [cmd for cmd in all_commands if not cmd.meta.hide]
        if not cmds:
            await session.send("没有找到对应的插件")
            return

        formatter = MarkdownTextFormatter()
        for cmd in cmds:
            formatter.add(cmd)
        md_help = formatter.format_node()

        md_image = await md2img(md_help, screenshot_option={"timeout": 60000})
        if md_image is None:
            logger.warning("md2img 生成图片失败，尝试发送文本帮助")
            await session.send("\n\n".join(cmd.get_help() for cmd in cmds))
            return

        await session.send([Image.of(raw=md_image, mime="image/png")])

    if plugin.available:
        await send_command_help(plugin.result)
        return

    namespaces = command_manager.get_loaded_namespaces
    namespaces = [ns for ns in namespaces if ns != "Alconna"]

    if not namespaces:
        await session.send("暂无可查询的插件帮助")
        return

    options = "\n".join(f"{index}. {name}" for index, name in enumerate(namespaces))
    resp = await session.prompt(
        f"请输入插件序号查看帮助：\n{options}",
        timeout_message=" ",
        block=False,
    )
    if resp is None:
        return

    plain = resp.extract_plain_text().strip()
    if not plain.isdigit():
        return

    index = int(plain)
    if not (0 <= index < len(namespaces)):
        await session.send("没有找到对应的插件")
        return

    await send_command_help(namespaces[index])
