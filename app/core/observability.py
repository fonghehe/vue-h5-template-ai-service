"""Low-cardinality metrics and tracing helpers."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from prometheus_client import Counter, Gauge, Histogram

AI_REQUESTS = Counter("ai_requests_total", "AI requests", ["path", "status"])
AI_DURATION = Histogram("ai_request_duration_seconds", "AI request duration", ["path"])
AI_TOKENS = Counter("ai_tokens_total", "Model tokens", ["kind", "model"])
ACTIVE_STREAMS = Gauge("active_streams", "Active SSE streams")
TOOL_CALLS = Counter("tool_calls_total", "Tool calls", ["tool", "status"])
PROVIDER_ERRORS = Counter("provider_errors_total", "Provider errors", ["provider", "kind"])


def configure_tracing(service_name: str) -> None:
    if not isinstance(trace.get_tracer_provider(), TracerProvider):
        trace.set_tracer_provider(TracerProvider(resource=Resource.create({"service.name": service_name})))


@contextmanager
def span(name: str, **attributes: object) -> Iterator[None]:
    tracer = trace.get_tracer("vue-h5-template-ai-service")
    with tracer.start_as_current_span(name, attributes={key: str(value) for key, value in attributes.items()}):
        yield
