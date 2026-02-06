import prometheus_client as prometheus_client
from prometheus_client import (
    Counter as Counter,
    Gauge as Gauge,
    Histogram as Histogram,
    Summary as Summary,
)

from arclet.entari import metadata, command, Session
from arclet.alconna import Alconna, Subcommand, CommandMeta
from arclet.entari.message import MessageChain

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


metrics_alc = Alconna(
    "metrics",
    Subcommand("status", help_text="查看机器人状态"),
    Subcommand("message", help_text="查看消息统计"),
    Subcommand("matcher", help_text="查看匹配器统计"),
    Subcommand("system", help_text="查看系统指标"),
    Subcommand("uptime", help_text="查看运行时间"),
    meta=CommandMeta(
        description="查询 Prometheus 指标数据",
        usage="/metrics",
        example="/metrics status",
    ),
)
metrics_disp = command.mount(metrics_alc)


@metrics_disp.assign("$main")
async def show_metrics_help(session: Session):
    """显示帮助信息"""
    help_text = (
        "📊 Prometheus 监控命令帮助\n"
        "用法: /metrics <子命令>\n\n"
        "可用子命令:\n"
        "  status  - 查看机器人状态\n"
        "  message - 查看消息统计\n"
        "  matcher - 查看匹配器统计\n"
        "  system  - 查看系统指标\n"
        "  uptime  - 查看运行时间\n"
    )
    msg = MessageChain([help_text])
    await session.send(msg)


@metrics_disp.assign("status")
async def show_bot_status(session: Session):
    """显示机器人状态"""
    status_info = get_bot_status()

    if status_info.error:
        error_msg = f"❌ 获取机器人状态失败: {status_info.error}"
        msg = MessageChain([error_msg])
        await session.send(msg)
        return

    if status_info.total_bots == 0:
        msg = MessageChain(["🤖 机器人状态: 没有在线机器人"])
        await session.send(msg)
        return

    response = f"🤖 机器人状态 (总计: {status_info.total_bots}个)\n"
    response += "-" * 30 + "\n"

    for bot in status_info.bots:
        response += f"Bot ID: {bot.bot_id}\n"
        response += f"平台: {bot.platform}\n"
        response += "状态: 🟢 在线\n"
        response += f"掉线次数: {bot.shutdown_count}\n"
        response += "-" * 20 + "\n"

    msg = MessageChain([response.rstrip("\n- ")])
    await session.send(msg)


@metrics_disp.assign("message")
async def show_message_stats(session: Session):
    """显示消息统计"""
    stats = get_message_stats()

    if stats.error:
        error_msg = f"❌ 获取消息统计失败: {stats.error}"
        msg = MessageChain([error_msg])
        await session.send(msg)
        return

    response = "💬 消息统计\n"
    response += "-" * 30 + "\n"
    response += f"总接收消息: {format_large_number(stats.total_received)}\n"
    response += f"总发送消息: {format_large_number(stats.total_sent)}\n\n"

    if stats.received_by_bot:
        response += "接收消息按机器人统计:\n"
        for bot_key, data in stats.received_by_bot.items():
            response += f"  {bot_key}: {format_large_number(data.count)}\n"
        response += "\n"

    if stats.sent_by_bot:
        response += "发送消息按机器人统计:\n"
        for bot_key, data in stats.sent_by_bot.items():
            response += f"  {bot_key}: {format_large_number(data.count)}\n"

    msg = MessageChain([response.rstrip()])
    await session.send(msg)


@metrics_disp.assign("matcher")
async def show_matcher_stats(session: Session):
    """显示匹配器统计"""
    stats = get_matcher_stats()

    if stats.error:
        error_msg = f"❌ 获取匹配器统计失败: {stats.error}"
        msg = MessageChain([error_msg])
        await session.send(msg)
        return

    response = "🔄 匹配器统计\n"
    response += "-" * 30 + "\n"
    response += f"总匹配器数量: {stats.total_matchers}\n"
    response += f"总调用次数: {format_large_number(stats.total_calls)}\n\n"

    if stats.top_matchers:
        response += "调用次数最多的匹配器:\n"
        for i, matcher in enumerate(stats.top_matchers, 1):
            avg_duration_ms = matcher.avg_duration * 1000  # 转换为毫秒
            response += (
                f"  {i}. {matcher.plugin_name}\n"
                f"     调用次数: {format_large_number(matcher.call_count)}\n"
                f"     平均耗时: {avg_duration_ms:.2f}ms\n"
            )
            if i < len(stats.top_matchers):
                response += "\n"

    msg = MessageChain([response])
    await session.send(msg)


@metrics_disp.assign("system")
async def show_system_metrics(session: Session):
    """显示系统指标"""
    metrics = get_system_metrics()

    if metrics.error:
        error_msg = f"❌ 获取系统指标失败: {metrics.error}"
        msg = MessageChain([error_msg])
        await session.send(msg)
        return

    response = "🖥️ 系统指标\n"
    response += "-" * 30 + "\n"
    response += f"启动时间: {metrics.start_time}\n"
    response += f"运行时间: {metrics.uptime}\n"

    msg = MessageChain([response])
    await session.send(msg)


@metrics_disp.assign("uptime")
async def show_uptime(session: Session):
    """显示运行时间"""
    metrics = get_system_metrics()

    if metrics.error:
        error_msg = f"❌ 获取运行时间失败: {metrics.error}"
        msg = MessageChain([error_msg])
        await session.send(msg)
        return

    response = f"⏱️ 运行时间: {metrics.uptime}\n"
    response += f"启动时间: {metrics.start_time}\n"

    msg = MessageChain([response])
    await session.send(msg)
