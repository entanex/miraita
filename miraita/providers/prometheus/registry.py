from __future__ import annotations

from typing import Any
from dataclasses import dataclass, asdict
from prometheus_client import REGISTRY
from prometheus_client.samples import Sample

from miraita import logger


@dataclass
class MetricFamily:
    """Prometheus 指标族"""

    name: str
    type: str
    help: str
    samples: list[Sample]

    def filter_samples(self, labels: dict[str, str] | None = None) -> list[Sample]:
        """根据标签过滤样本"""
        if not labels:
            return self.samples
        return [
            s
            for s in self.samples
            if all(s.labels.get(k) == v for k, v in labels.items())
        ]


@dataclass
class MetricCollection:
    """Prometheus 指标集合"""

    metrics: list[MetricFamily]
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "metrics": [
                {
                    "name": m.name,
                    "type": m.type,
                    "help": m.help,
                    "samples": [
                        {
                            "name": s.name,
                            "labels": s.labels,
                            "value": s.value,
                            "timestamp": float(s.timestamp)
                            if s.timestamp is not None
                            else None,
                        }
                        for s in m.samples
                    ],
                }
                for m in self.metrics
            ],
            "error": self.error,
        }

    def list_all(self) -> list[dict[str, Any]]:
        return sorted(
            [
                {
                    "name": m.name,
                    "type": m.type,
                    "help": m.help,
                    "sample_count": len(m.samples),
                }
                for m in self.metrics
            ],
            key=lambda x: x["name"],
        )

    def find_by_name(self, metric_name: str) -> list[MetricFamily]:
        return [
            m
            for m in self.metrics
            if (
                m.name == metric_name
                or m.name.startswith(metric_name + "_")
                or metric_name.startswith(m.name + "_")
            )
        ]

    def find_by_type(self, metric_type: str) -> list[MetricFamily]:
        return [m for m in self.metrics if m.type == metric_type]

    def search(self, keyword: str) -> list[dict[str, Any]]:
        kw = keyword.lower()
        return [
            {
                "name": m.name,
                "type": m.type,
                "help": m.help,
                "sample_count": len(m.samples),
            }
            for m in self.metrics
            if kw in m.name.lower() or kw in m.help.lower() or kw in m.type.lower()
        ]


def collect_metrics() -> MetricCollection:
    try:
        families: list[MetricFamily] = []

        for fam in REGISTRY.collect():
            families.append(
                MetricFamily(
                    name=fam.name,
                    type=fam.type,
                    help=fam.documentation,
                    samples=fam.samples,
                )
            )

        logger.debug(f"Collected {len(families)} metric families")
        return MetricCollection(families)

    except Exception as e:
        logger.exception("Failed to collect metrics")
        return MetricCollection(metrics=[], error=str(e))


def get_metrics() -> dict[str, Any]:
    return collect_metrics().to_dict()


def get_metrics_by_name(metric_name: str) -> dict[str, Any]:
    """根据指标名称获取"""
    coll = collect_metrics()
    matched = coll.find_by_name(metric_name)
    return {
        "metric_name": metric_name,
        "metrics": [asdict(m) for m in matched],
        "count": len(matched),
        "error": coll.error,
    }


def get_metrics_by_type(metric_type: str) -> dict[str, Any]:
    """根据指标类型获取"""
    coll = collect_metrics()
    matched = coll.find_by_type(metric_type)
    return {
        "type": metric_type,
        "metrics": [asdict(m) for m in matched],
        "count": len(matched),
        "error": coll.error,
    }


def get_metric_values(
    metric_name: str, labels: dict[str, str] | None = None
) -> list[tuple[dict[str, str], float]]:
    """
    获取指定指标的样本值
    """
    coll = collect_metrics()
    result: list[tuple[dict[str, str], float]] = []

    for fam in coll.find_by_name(metric_name):
        for s in fam.filter_samples(labels):
            # Counter 类型仅保留 *_total
            if fam.type == "counter" and not s.name.endswith("_total"):
                continue
            result.append((s.labels, s.value))
    return result


def list_all_metrics() -> list[dict[str, Any]]:
    """列出所有指标的概要信息"""
    return collect_metrics().list_all()


def search_metrics(keyword: str) -> list[dict[str, Any]]:
    """搜索包含关键字的指标"""
    return collect_metrics().search(keyword)


def parse_metric_filter(metric_query: str) -> tuple[str, dict[str, str]]:
    """
    解析指标查询表达式

    示例：
        ```
        http_requests_total{method="GET",code="200"}
        ```
    """
    try:
        if "{" not in metric_query:
            return metric_query.strip(), {}

        name, filter_part = metric_query.split("{", 1)
        filter_part = filter_part.rstrip("}")
        labels = {}
        for pair in filter_part.split(","):
            if "=" in pair:
                k, v = pair.split("=", 1)
                labels[k.strip()] = v.strip("\"'")
        return name.strip(), labels
    except Exception as e:
        logger.error(f"Failed to parse metric filter: {e}")
        return metric_query.strip(), {}
