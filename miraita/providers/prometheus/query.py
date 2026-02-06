import time
from datetime import datetime, timedelta

from .schema import (
    BotInfo,
    BotStatusResponse,
    BotMessageStats,
    MessageStatsResponse,
    MatcherStats,
    MatcherStatsResponse,
    SystemMetricsResponse,
)
from .metrics import (
    miraita_start_at_gauge,
    bot_nums_gauge,
    bot_shutdown_counter,
    received_messages_counter,
    sent_messages_counter,
    matcher_calling_counter,
    matcher_duration_histogram,
)


def format_large_number(num: float) -> str:
    """格式化大数字，添加K、M、B等单位"""
    if num == 0:
        return "0"

    abs_num = abs(num)

    if abs_num >= 1_000_000_000:  # 十亿
        return f"{num / 1_000_000_000:.1f}B"
    elif abs_num >= 1_000_000:  # 百万
        return f"{num / 1_000_000:.1f}M"
    elif abs_num >= 1_000:  # 千
        return f"{num / 1_000:.1f}K"
    else:
        return f"{num:.0f}"


def get_bot_status() -> BotStatusResponse:
    """获取机器人状态信息"""
    try:
        bot_samples = list(bot_nums_gauge.collect())[0].samples
        online_bots = [sample for sample in bot_samples if sample.value > 0]

        shutdown_samples = list(bot_shutdown_counter.collect())[0].samples
        shutdown_counts = {}
        for sample in shutdown_samples:
            if "_total" in sample.name:
                bot_id = sample.labels.get("bot_id", "unknown")
                platform = sample.labels.get("platform", "unknown")
                bot_key = f"{bot_id}_{platform}"
                shutdown_counts[bot_key] = int(sample.value)

        bots = []
        for bot_sample in online_bots:
            bot_id = bot_sample.labels["bot_id"]
            platform = bot_sample.labels["platform"]
            bot_key = f"{bot_id}_{platform}"
            shutdown_count = shutdown_counts.get(bot_key, 0)

            bots.append(
                BotInfo(
                    bot_id=bot_id,
                    platform=platform,
                    status="online",
                    shutdown_count=shutdown_count,
                )
            )

        return BotStatusResponse(total_bots=len(online_bots), bots=bots)
    except Exception as e:
        return BotStatusResponse(total_bots=0, bots=[], error=str(e))


def get_message_stats() -> MessageStatsResponse:
    """获取消息统计信息"""
    try:
        received_samples = list(received_messages_counter.collect())[0].samples
        received_total = 0
        received_by_bot = {}

        for sample in received_samples:
            if sample.name.endswith("_total"):
                received_total += sample.value
                bot_id = sample.labels.get("bot_id", "unknown")
                platform = sample.labels.get("platform", "unknown")

                bot_key = f"{bot_id}({platform})"
                if bot_key not in received_by_bot:
                    received_by_bot[bot_key] = BotMessageStats(
                        bot_id=bot_id,
                        platform=platform,
                        count=0,
                    )
                received_by_bot[bot_key].count += sample.value

        sent_samples = list(sent_messages_counter.collect())[0].samples
        sent_total = 0
        sent_by_bot = {}

        for sample in sent_samples:
            if sample.name.endswith("_total"):
                sent_total += sample.value
                bot_id = sample.labels.get("bot_id", "unknown")
                platform = sample.labels.get("platform", "unknown")

                bot_key = f"{bot_id}({platform})"
                if bot_key not in sent_by_bot:
                    sent_by_bot[bot_key] = BotMessageStats(
                        bot_id=bot_id,
                        platform=platform,
                        count=0,
                    )
                sent_by_bot[bot_key].count += sample.value

        return MessageStatsResponse(
            total_received=received_total,
            total_sent=sent_total,
            received_by_bot=received_by_bot,
            sent_by_bot=sent_by_bot,
        )
    except Exception as e:
        return MessageStatsResponse(
            total_received=0,
            total_sent=0,
            received_by_bot={},
            sent_by_bot={},
            error=str(e),
        )


def get_matcher_stats(limit: int = 10) -> MatcherStatsResponse:
    """获取匹配器统计信息"""
    try:
        calling_samples = list(matcher_calling_counter.collect())[0].samples

        duration_data = list(matcher_duration_histogram.collect())
        duration_samples = []
        for metric_family in duration_data:
            for sample in metric_family.samples:
                # 获取 _sum 指标（总执行时间）
                if sample.name.endswith("_sum"):
                    duration_samples.append(sample)

        matcher_stats = {}

        for sample in calling_samples:
            if sample.name.endswith("_total"):
                plugin_name = sample.labels.get("plugin_name", "unknown")
                call_count = sample.value

                if plugin_name not in matcher_stats:
                    matcher_stats[plugin_name] = MatcherStats(
                        plugin_name=plugin_name,
                        call_count=0,
                        total_duration=0,
                        avg_duration=0,
                    )

                matcher_stats[plugin_name].call_count += call_count

        for sample in duration_samples:
            plugin_name = sample.labels.get("plugin_name", "unknown")

            if plugin_name in matcher_stats:
                matcher_stats[plugin_name].total_duration += sample.value

        for matcher_name, stats in matcher_stats.items():
            if stats.call_count > 0:
                stats.avg_duration = stats.total_duration / stats.call_count
            else:
                stats.avg_duration = 0

        sorted_matchers = sorted(
            matcher_stats.values(), key=lambda x: x.call_count, reverse=True
        )

        total_calls = sum(m.call_count for m in sorted_matchers)

        return MatcherStatsResponse(
            total_matchers=len(sorted_matchers),
            top_matchers=sorted_matchers[:limit],
            total_calls=total_calls,
        )
    except Exception as e:
        return MatcherStatsResponse(
            total_matchers=0, top_matchers=[], total_calls=0, error=str(e)
        )


def get_system_metrics() -> SystemMetricsResponse:
    """获取系统指标"""
    try:
        start_time_samples = list(miraita_start_at_gauge.collect())[0].samples
        if start_time_samples:
            start_timestamp = start_time_samples[0].value
            current_time = time.time()
            uptime_seconds = current_time - start_timestamp
            uptime_str = str(timedelta(seconds=int(uptime_seconds)))

            start_time_formatted = datetime.fromtimestamp(start_timestamp).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        else:
            uptime_str = "未知"
            start_time_formatted = "未知"
            uptime_seconds = 0

        return SystemMetricsResponse(
            uptime=uptime_str,
            start_time=start_time_formatted,
            uptime_seconds=uptime_seconds,
        )
    except Exception as e:
        return SystemMetricsResponse(
            uptime="未知", start_time="未知", uptime_seconds=0, error=str(e)
        )
