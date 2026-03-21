import prometheus_client as prometheus_client
from prometheus_client import (
    Counter as Counter,
    Gauge as Gauge,
    Histogram as Histogram,
    Summary as Summary,
)

from arclet.entari import metadata, command, Session
from arclet.alconna import Alconna, Subcommand, CommandMeta, Namespace, config

from . import listener as listener
from .query import (
    get_bot_status,
    get_message_stats,
    get_matcher_stats,
    get_system_metrics,
    format_large_number,
)


metadata(
    name="Prometheus 监控",
    author=["Komorebi <mute231010@gmail.com>"],
    description="Prometheus 监控",
    classifier=["服务"],
)

ns = Namespace("Prometheus 监控")
config.namespaces["Prometheus 监控"] = ns


metrics_alc = Alconna(
    "metrics",
    Subcommand("status", help_text="查看机器人状态"),
    Subcommand("message", help_text="查看消息统计"),
    Subcommand("matcher", help_text="查看匹配器统计"),
    Subcommand("system", help_text="查看系统指标"),
    meta=CommandMeta(
        description="查询 Prometheus 指标数据",
        usage="/metrics",
        example="/metrics",
    ),
    namespace=ns,
)
metrics_disp = command.mount(metrics_alc)


def _render_bot_status_lines():
    status_info = get_bot_status()

    if status_info.error:
        return status_info, [f"获取机器人状态失败: {status_info.error}"]

    lines = [f"在线机器人: {status_info.total_bots}"]
    if status_info.total_bots == 0:
        lines.append("实例: 无在线机器人")
        return status_info, lines

    for bot in status_info.bots:
        lines.append(
            f"- {bot.bot_id} ({bot.platform}) | 状态: 在线 | 掉线次数: {bot.shutdown_count}"  # noqa: E501
        )
    return status_info, lines


def _render_message_stats_lines():
    stats = get_message_stats()

    if stats.error:
        return stats, [f"获取消息统计失败: {stats.error}"]

    lines = [
        f"接收消息: {format_large_number(stats.total_received)}",
        f"发送消息: {format_large_number(stats.total_sent)}",
    ]

    if stats.received_by_bot:
        lines.append("接收分布:")
        for bot_key, data in sorted(stats.received_by_bot.items()):
            lines.append(f"- {bot_key}: {format_large_number(data.count)}")

    if stats.sent_by_bot:
        lines.append("发送分布:")
        for bot_key, data in sorted(stats.sent_by_bot.items()):
            lines.append(f"- {bot_key}: {format_large_number(data.count)}")

    return stats, lines


def _render_matcher_stats_lines(limit: int = 5):
    stats = get_matcher_stats(limit=limit)

    if stats.error:
        return stats, [f"获取匹配器统计失败: {stats.error}"]

    lines = [
        f"匹配器数量: {stats.total_matchers}",
        f"总调用次数: {format_large_number(stats.total_calls)}",
    ]

    if stats.top_matchers:
        lines.append(f"Top {len(stats.top_matchers)}:")
        for index, matcher in enumerate(stats.top_matchers, 1):
            avg_duration_ms = matcher.avg_duration * 1000
            lines.append(
                f"{index}. {matcher.plugin_name} | 调用: {format_large_number(matcher.call_count)} | 平均耗时: {avg_duration_ms:.2f}ms"  # noqa: E501
            )

    return stats, lines


def _render_system_metrics_lines():
    metrics = get_system_metrics()

    if metrics.error:
        return metrics, [f"获取系统指标失败: {metrics.error}"]

    lines = [
        f"启动时间: {metrics.start_time}",
        f"运行时间: {metrics.uptime}",
    ]
    return metrics, lines


@metrics_disp.assign("$main")
async def show_metrics_summary(session: Session):
    """显示聚合概览"""
    _, status_lines = _render_bot_status_lines()
    _, message_lines = _render_message_stats_lines()
    _, matcher_lines = _render_matcher_stats_lines(limit=3)
    _, system_lines = _render_system_metrics_lines()

    summary_text = (
        "Prometheus 指标概览\n"
        "\n[机器人]\n"
        f"{chr(10).join(status_lines)}\n"
        "\n[消息]\n"
        f"{chr(10).join(message_lines)}\n"
        "\n[匹配器]\n"
        f"{chr(10).join(matcher_lines)}\n"
        "\n[系统]\n"
        f"{chr(10).join(system_lines)}\n"
        "\n子命令: /metrics status | message | matcher | system"
    )
    await session.send(summary_text)


@metrics_disp.assign("status")
async def show_bot_status(session: Session):
    """显示机器人状态"""
    _, lines = _render_bot_status_lines()
    await session.send("机器人状态\n" + "\n".join(lines))


@metrics_disp.assign("message")
async def show_message_stats(session: Session):
    """显示消息统计"""
    _, lines = _render_message_stats_lines()
    await session.send("消息统计\n" + "\n".join(lines))


@metrics_disp.assign("matcher")
async def show_matcher_stats(session: Session):
    """显示匹配器统计"""
    _, lines = _render_matcher_stats_lines(limit=10)
    await session.send("匹配器统计\n" + "\n".join(lines))


@metrics_disp.assign("system")
async def show_system_metrics(session: Session):
    """显示系统指标"""
    _, lines = _render_system_metrics_lines()
    await session.send("系统指标\n" + "\n".join(lines))
