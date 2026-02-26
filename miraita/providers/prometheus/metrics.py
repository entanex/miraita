from prometheus_client import Counter, Gauge, REGISTRY, Histogram
from arclet.entari import keeping


miraita_start_at_gauge = keeping(
    "miraita_start_at_gauge",
    obj_factory=lambda: Gauge("miraita_start_at", "Start time of the bot"),
    dispose=lambda gauge: REGISTRY.unregister(gauge),
)

bot_nums_gauge = keeping(
    "bot_nums_gauge",
    obj_factory=lambda: Gauge(
        "bot_nums", "Total number of bots", ["bot_id", "platform"]
    ),
    dispose=lambda gauge: REGISTRY.unregister(gauge),
)

bot_shutdown_counter = keeping(
    "bot_shutdown_counter",
    obj_factory=lambda: Counter(
        "bot_shutdown", "Total number of bots shutdown", ["bot_id", "platform"]
    ),
    dispose=lambda counter: REGISTRY.unregister(counter),
)

received_messages_counter = keeping(
    "received_messages_counter",
    obj_factory=lambda: Counter(
        "miraita_received_messages",
        "Total number of received messages",
        ["bot_id", "platform", "user_id"],
    ),
    dispose=lambda counter: REGISTRY.unregister(counter),
)

sent_messages_counter = keeping(
    "sent_messages_counter",
    obj_factory=lambda: Counter(
        "miriata_sent_messages",
        "Total number of sent messages",
        ["bot_id", "platform", "user_id"],
    ),
    dispose=lambda counter: REGISTRY.unregister(counter),
)

matcher_calling_counter = keeping(
    "matcher_calling_counter",
    obj_factory=lambda: Counter(
        "nonebot_matcher_calling",
        "Total number of matcher calling",
        ["plugin_name"],
    ),
    dispose=lambda counter: REGISTRY.unregister(counter),
)

matcher_duration_histogram = keeping(
    "matcher_duration_histogram",
    obj_factory=lambda: Histogram(
        "miraita_matcher_duration_seconds",
        "Histogram of matcher duration in seconds",
        ["plugin_name"],
        buckets=(
            0.005,
            0.01,
            0.025,
            0.05,
            0.075,
            0.1,
            0.25,
            0.5,
            0.75,
            1.0,
            2.5,
            5.0,
            7.5,
            10.0,
            30.0,
            60.0,
        ),
    ),
    dispose=lambda histogram: REGISTRY.unregister(histogram),
)
