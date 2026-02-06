from arclet.entari import keeping
from fastapi import APIRouter, Response
from prometheus_client import generate_latest, REGISTRY, CONTENT_TYPE_LATEST

from miraita.providers.prometheus import Counter  # entari: plugin

router = APIRouter(tags=["Metrics"])

metrics_request_counter = keeping(
    "metrics_request_counter",
    obj_factory=lambda: Counter("miraita_metrics_requests", "Total number of requests"),
    dispose=lambda counter: REGISTRY.unregister(counter),
)


@router.get("/")
async def prometheus() -> Response:
    """Prometheus metrics endpoint."""
    metrics_request_counter.inc()
    return Response(
        generate_latest(),
        status_code=200,
        headers={"Content-Type": CONTENT_TYPE_LATEST},
    )
