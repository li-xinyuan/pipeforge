"""Prometheus-style metrics collection for ConfigForge.

Uses a lightweight in-memory counter/histogram implementation to avoid
hard dependency on prometheus_client. Exposes metrics in Prometheus
text exposition format via /api/metrics.
"""

import threading
import time
from collections import defaultdict

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

# ── HTTP metrics ────────────────────────────────────────────────
http_requests_total = Counter(
    "configforge_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

http_request_duration_seconds = Histogram(
    "configforge_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# ── Pipeline metrics ────────────────────────────────────────────
pipeline_executions_total = Counter(
    "configforge_pipeline_executions_total",
    "Total pipeline executions",
    ["status"],
)

pipeline_duration_seconds = Histogram(
    "configforge_pipeline_duration_seconds",
    "Pipeline execution duration in seconds",
    buckets=(0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0),
)

# ── System metrics ──────────────────────────────────────────────
active_connections = Gauge(
    "configforge_active_connections",
    "Number of active database connections",
)

configs_total = Gauge(
    "configforge_configs_total",
    "Total number of saved configurations",
)


def record_http_request(method: str, endpoint: str, status: int, duration: float) -> None:
    """Record an HTTP request metric."""
    http_requests_total.labels(method=method, endpoint=endpoint, status=str(status)).inc()
    http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)


def record_pipeline_execution(status: str, duration: float) -> None:
    """Record a pipeline execution metric."""
    pipeline_executions_total.labels(status=status).inc()
    pipeline_duration_seconds.observe(duration)


def get_metrics() -> str:
    """Return metrics in Prometheus text exposition format."""
    return generate_latest().decode("utf-8")


def get_metrics_content_type() -> str:
    """Return the content type for Prometheus metrics."""
    return CONTENT_TYPE_LATEST
