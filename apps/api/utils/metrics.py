"""
Prometheus Metrics Module
Exposes /metrics endpoint and application-level counters, histograms, and gauges.

All metrics are no-ops when prometheus_client is not installed, so the rest
of the application can import and use them unconditionally.
"""
import logging

from flask import Blueprint, Response

from extensions import limiter

logger = logging.getLogger(__name__)

try:
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        Counter,
        Gauge,
        Histogram,
        generate_latest,
    )

    RENDERS_TOTAL = Counter(
        "yantra4d_renders_total",
        "Total render operations",
        ["engine", "format", "tier"],
    )

    RENDER_DURATION = Histogram(
        "yantra4d_render_duration_seconds",
        "Render wall-clock duration in seconds",
        ["engine"],
        buckets=(0.5, 1, 2, 5, 10, 30, 60, 120, 300),
    )

    CACHE_HITS = Counter(
        "yantra4d_cache_hits_total",
        "Render cache hits (L1 or L2)",
    )

    CACHE_MISSES = Counter(
        "yantra4d_cache_misses_total",
        "Render cache misses",
    )

    AI_SESSIONS_ACTIVE = Gauge(
        "yantra4d_ai_sessions_active",
        "Currently active AI chat sessions",
    )

    _PROMETHEUS_AVAILABLE = True

except ImportError:
    logger.info("prometheus_client not installed; metrics disabled")

    class _Noop:
        """Drop-in stub so callers never need to guard imports."""
        def inc(self, *a, **kw): pass
        def dec(self, *a, **kw): pass
        def set(self, *a, **kw): pass
        def observe(self, *a, **kw): pass
        def labels(self, *a, **kw): return self
        def time(self): return _NoopCtx()

    class _NoopCtx:
        def __enter__(self): return self
        def __exit__(self, *a): pass

    RENDERS_TOTAL = _Noop()
    RENDER_DURATION = _Noop()
    CACHE_HITS = _Noop()
    CACHE_MISSES = _Noop()
    AI_SESSIONS_ACTIVE = _Noop()
    _PROMETHEUS_AVAILABLE = False


# ── Blueprint ────────────────────────────────────────────────────────────

metrics_bp = Blueprint("metrics", __name__)


@metrics_bp.route("/metrics")
@limiter.exempt
def prometheus_metrics():
    """Prometheus scrape endpoint. Returns empty body when library is absent."""
    if not _PROMETHEUS_AVAILABLE:
        return Response("# prometheus_client not installed\n", mimetype="text/plain")
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)
