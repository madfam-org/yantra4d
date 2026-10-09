"""
Prometheus Metrics Module
Exposes /metrics endpoint and application-level counters, histograms, and gauges.

All metrics are no-ops when prometheus_client is not installed, so the rest
of the application can import and use them unconditionally.

/metrics is served on the same port (5000) that cloudflared publishes as
api.yantra4d.com, so it answers only in-cluster scrapers and 404s everything
else -- see ``is_internal_scrape``.
"""
import ipaddress
import logging

from flask import Blueprint, Response, abort, request

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


# ── Internal-only guard ──────────────────────────────────────────────────
#
# Every public request arrives through cloudflared, which forwards the public
# Host (api.yantra4d.com) and always adds the Cloudflare edge headers. The
# in-cluster Prometheus scrapes the pod IP directly: Host is <podIP>:5000 (or a
# *.svc name) and no Cloudflare header is present. Anything that looks public
# gets the app's ordinary 404 -- not 403, so the route does not advertise itself.

CLOUDFLARE_EDGE_HEADERS = ("cf-connecting-ip", "cf-ray", "cdn-loop")


def _strip_port(host: str) -> str:
    """Return the host part of a Host header value, lower-cased, port removed."""
    host = host.strip().lower()
    if host.startswith("["):  # [::1]:5000
        end = host.find("]")
        return host[1:end] if end != -1 else host
    if host.count(":") == 1:  # name:port or ipv4:port
        return host.split(":", 1)[0]
    return host  # bare name, bare IPv4, or bare IPv6 literal


def is_internal_host(host: str) -> bool:
    """True for Hosts only an in-cluster caller would send.

    Allowed: IP literals, ``localhost``, ``*.svc`` / ``*.svc.cluster.local``
    Service names, and bare names without dots. Anything else -- in particular
    a public FQDN such as ``api.yantra4d.com`` -- is treated as public.
    """
    name = _strip_port(host)
    if not name:
        return False
    try:
        ipaddress.ip_address(name)
        return True
    except ValueError:
        pass
    if name == "localhost":
        return True
    if name.endswith((".svc", ".svc.cluster.local")):
        return True
    return "." not in name


def is_internal_scrape(headers) -> bool:
    """True when request headers look like an in-cluster scraper, not the tunnel."""
    if any(headers.get(name) is not None for name in CLOUDFLARE_EDGE_HEADERS):
        return False
    return is_internal_host(headers.get("Host", ""))


# ── Blueprint ────────────────────────────────────────────────────────────

metrics_bp = Blueprint("metrics", __name__)


@metrics_bp.route("/metrics")
@limiter.exempt
def prometheus_metrics():
    """Prometheus scrape endpoint. Returns empty body when library is absent."""
    if not is_internal_scrape(request.headers):
        abort(404)
    if not _PROMETHEUS_AVAILABLE:
        return Response("# prometheus_client not installed\n", mimetype="text/plain")
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)
