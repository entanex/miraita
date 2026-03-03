import textwrap

from nepattern import Empty, ANY, AnyString
from tarina import lang
from arclet.alconna import AllParam
from arclet.alconna.args import Args, Arg
from arclet.alconna.base import Subcommand, Option
from arclet.alconna.formatter import TextFormatter, Trace


class MarkdownTextFormatter(TextFormatter):
    @staticmethod
    def _escape_inline(text: str) -> str:
        return (
            text.replace("\\", "\\\\")
            .replace("`", "\\`")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    def format(self, trace: Trace) -> str:
        """头部节点的描述"""
        root, separators = trace.head, trace.separators
        params, notice = self.parameters(trace.args)
        help_string = f"{desc}" if (desc := root.get("description")) else root["name"]
        usage = (
            textwrap.dedent(str(usage)).strip() if (usage := root.get("usage")) else ""
        )
        example = (
            f"## {lang.require('format', 'example')}\n"
            + f"```shell\n{textwrap.dedent(str(example)).strip()}\n```"
            if (example := root.get("example"))
            else ""
        )
        command_string = root["name"]
        if not command_string.startswith("/"):
            command_string = f"/{command_string}"
        body = self.body(trace.body)
        signature = f"{command_string}{separators[0]}{params}".strip()
        lines = [
            f"# {help_string}",
            "",
            f"## {lang.require('tools', 'format.md.title')}",
            "```shell",
            signature,
            "```",
        ]
        if notice:
            lines.extend(
                [
                    "",
                    f"## {lang.require('format', 'notice')}",
                    *[f"- `{item}`" for item in notice],
                ]
            )
        if usage:
            lines.extend(
                [
                    "",
                    f"## {lang.require('format', 'usage')}",
                    usage,
                ]
            )
        if body:
            lines.extend(["", body])
        if example:
            lines.extend(["", example])
        return "\n".join(lines)

    def param(self, parameter: Arg) -> str:
        """对单个参数的描述"""
        name = parameter.name
        if str(parameter.value).strip("'\"") == name:
            return f"[{name}]" if parameter.optional else name
        if parameter.hidden:
            return f"[{name}]" if parameter.optional else f"<{name}>"
        if parameter.value is AllParam:
            return f"<...{name}>"
        arg = f"[{name}" if parameter.optional else f"<{name}"
        if parameter.value not in (ANY, AnyString):
            arg += f": {parameter.value}"
        if parameter.field.display is not Empty:
            arg += f" = {parameter.field.display}"
        return f"{arg}]" if parameter.optional else f"{arg}>"

    def parameters(self, args: Args) -> tuple[str, list[str] | None]:  # type: ignore
        """参数列表的描述"""
        res = ""
        for arg in args.argument:
            if arg.name.startswith("_key_"):
                continue
            if len(arg.separators) == 1:
                sep = " " if arg.separators[0] == " " else f" {arg.separators[0]!r} "
            else:
                sep = f"[{'|'.join(arg.separators)!r}]"
            res += self.param(arg) + sep
        notice = [(arg.name, arg.notice) for arg in args.argument if arg.notice]
        return (
            (res[:-1], [f"{v[0]}: {v[1]}" for v in notice])
            if notice
            else (res[:-1], None)
        )

    def opt(self, node: Option) -> str:
        alias_text = (
            " ".join(node.requires)
            + (" " if node.requires else "")
            + "│".join(node.aliases)
        )
        help_text = "Unknown" if node.help_text == node.dest else node.help_text
        param, notice = self.parameters(node.args)
        title = self._escape_inline(
            alias_text + (tuple(node.separators)[0] if param else "") + param.strip(" ")
        )
        lines = [
            f"- `{title}`: {help_text}",
        ]
        if notice:
            lines.append("")
            lines.append(f"**{lang.require('format', 'notice')}**")
            lines.extend([f"- `{item}`" for item in notice])
        return "\n".join(lines)

    def sub(self, node: Subcommand) -> str:
        """对单个子命令的描述"""
        name = (
            " ".join(node.requires)
            + (" " if node.requires else "")
            + "│".join(node.aliases)
        )
        opt_string = "\n".join(
            [self.opt(opt) for opt in node.options if isinstance(opt, Option)]
        )
        sub_string = "\n\n".join(
            [self.sub(sub) for sub in node.options if isinstance(sub, Subcommand)]  # type: ignore
        )
        opt_help = (
            f"#### {lang.require('format', 'subcommands.opts')}\n" if opt_string else ""
        )
        sub_help = (
            f"#### {lang.require('format', 'subcommands.subs')}\n" if sub_string else ""
        )
        param, notice = self.parameters(node.args)
        help_text = "Unknown" if node.help_text == node.dest else node.help_text
        title = self._escape_inline(
            f"{name + (tuple(node.separators)[0] if param else '')}{param}"
        )
        lines = [
            f"- `{title}`: {help_text}",
        ]
        if notice:
            lines.append("")
            lines.append(f"**{lang.require('format', 'notice')}**")
            lines.extend([f"- `{item}`" for item in notice])
        if sub_string:
            lines.extend(["", sub_help + sub_string])
        if opt_string:
            lines.extend(["", opt_help + opt_string])
        return "\n".join(lines)

    def body(self, parts: list[Option | Subcommand]) -> str:
        """子节点列表的描述"""
        option_string = "\n\n".join(
            [
                self.opt(opt)
                for opt in parts
                if isinstance(opt, Option) and opt.name not in self.ignore_names
            ]
        )
        subcommand_string = "\n\n".join(
            [self.sub(sub) for sub in parts if isinstance(sub, Subcommand)]
        )
        option_help = (
            f"## {lang.require('format', 'options')}\n" if option_string else ""
        )
        subcommand_help = (
            f"## {lang.require('format', 'subcommands')}\n" if subcommand_string else ""
        )
        return f"{subcommand_help}{subcommand_string}{option_help}{option_string}"
