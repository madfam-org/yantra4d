"""
Health Blueprint
Provides /api/health, /api/health/live, and /api/health/ready endpoints.
"""
import logging
import os
import resource

from flask import Blueprint, jsonify

from config import Config
from extensions import limiter
from services.engine.render_gc import HIGH_WATER, volume_usage

logger = logging.getLogger(__name__)

health_bp = Blueprint('health', __name__)


def _check_openscad() -> tuple[bool, str]:
    """Check if OpenSCAD binary is available."""
    available = os.path.exists(Config.OPENSCAD_PATH)
    return available, "available" if available else "binary not found"


def _check_redis() -> tuple[bool, str]:
    """Ping Redis if configured. Returns (ok, detail)."""
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        return True, "not configured (optional)"
    try:
        import redis as redis_lib
        client = redis_lib.from_url(redis_url, socket_connect_timeout=2)
        client.ping()
        return True, "connected"
    except Exception as e:
        return False, f"unreachable: {e}"


def _check_analytics_db() -> tuple[bool, str]:
    """Check analytics DB connectivity via SQLAlchemy."""
    try:
        from sqlalchemy import text

        from extensions import db
        db.session.execute(text("SELECT 1"))
        db.session.rollback()  # don't hold open transactions
        uri = Config.SQLALCHEMY_DATABASE_URI
        if uri.startswith("postgresql"):
            return True, "postgresql connected"
        return True, "sqlite connected"
    except Exception as e:
        return False, f"unreachable: {e}"


def _check_mqtt() -> tuple[bool, str]:
    """Check MQTT telemetry service connectivity."""
    try:
        from services.core.mqtt_telemetry import telemetry_service
        if not telemetry_service.enabled:
            return True, "not enabled (optional)"
        return telemetry_service.connected, "connected" if telemetry_service.connected else "disconnected"
    except Exception as e:
        return False, str(e)


def _check_render_worker() -> tuple[bool, str]:
    """Check render worker heartbeat freshness."""
    try:
        from services.engine.render_orchestrator import get_render_worker_status

        status = get_render_worker_status()
        detail_parts = []
        if status["age_seconds"] is None:
            detail_parts.append("heartbeat missing")
        else:
            detail_parts.append(f"heartbeat age {status['age_seconds']}s")
        if status["queue_depth"] is not None:
            detail_parts.append(f"queue depth {status['queue_depth']}")
        if status["active_jobs"] is not None:
            detail_parts.append(f"active jobs {status['active_jobs']}")

        return status["available"], "; ".join(detail_parts)
    except Exception as e:
        return False, f"unreachable: {e}"


def _check_disk_space() -> tuple[bool, str]:
    """Check headroom on the render output volume.

    STATIC_DIR is an emptyDir with its own sizeLimit, which is far smaller than
    the node filesystem backing it. shutil.disk_usage() reports the node — it
    would happily report hundreds of GB free while the volume sits one render
    away from a kubelet eviction. Measure the volume against its own limit.
    """
    try:
        used, limit = volume_usage()
        if limit <= 0:
            return True, "no volume limit configured"
        pct_used = (used / limit) * 100
        free_mb = (limit - used) / (1024 * 1024)
        # The GC reclaims at HIGH_WATER; anything past that means it is losing
        # the race against inbound renders and eviction is imminent.
        ok = pct_used < HIGH_WATER * 100
        return ok, (
            f"{used / (1024 * 1024):.0f}MB used of {limit // (1024 * 1024)}MB "
            f"({pct_used:.1f}%, {free_mb:.0f}MB free)"
        )
    except Exception as e:
        return False, str(e)


def _check_memory() -> tuple[bool, str]:
    """Check process memory usage."""
    try:
        usage = resource.getrusage(resource.RUSAGE_SELF)
        rss_mb = usage.ru_maxrss / 1024  # macOS returns bytes, Linux returns KB
        if os.uname().sysname == "Linux":
            rss_mb = usage.ru_maxrss / 1024
        else:
            rss_mb = usage.ru_maxrss / (1024 * 1024)
        ok = rss_mb < 2048  # Under 2GB
        return ok, f"{rss_mb:.0f}MB RSS"
    except Exception as e:
        return False, str(e)


def _env_bool(name: str, default: bool = False) -> bool:
    """Parse common boolean env var values."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


@health_bp.route('/api/health/live')
@limiter.exempt
def liveness():
    """Liveness probe — always 200 unless process is hung."""
    return jsonify({"status": "alive"}), 200


@health_bp.route('/api/health/ready')
@limiter.exempt
def readiness():
    """Readiness probe — checks all subsystems."""
    checks = {}
    overall = "healthy"
    render_worker_required = _env_bool("RENDER_WORKER_REQUIRED", False)

    # Optional: OpenSCAD (platform supports WASM fallback)
    ok, detail = _check_openscad()
    checks["openscad"] = {"ok": ok, "detail": detail}
    if not ok and overall != "unhealthy":
        overall = "degraded"

    # Optional: Redis
    ok, detail = _check_redis()
    checks["redis"] = {"ok": ok, "detail": detail}
    if not ok and "not configured" not in detail and overall != "unhealthy":
        overall = "degraded"

    # Optional: Analytics DB
    ok, detail = _check_analytics_db()
    checks["analytics_db"] = {"ok": ok, "detail": detail}
    if not ok and overall != "unhealthy":
        overall = "degraded"

    # Optional: Disk space
    ok, detail = _check_disk_space()
    checks["disk"] = {"ok": ok, "detail": detail}
    if not ok and overall != "unhealthy":
        overall = "degraded"

    # Optional: Memory
    ok, detail = _check_memory()
    checks["memory"] = {"ok": ok, "detail": detail}
    if not ok and overall != "unhealthy":
        overall = "degraded"

    # Optional: MQTT
    ok, detail = _check_mqtt()
    checks["mqtt"] = {"ok": ok, "detail": detail}
    if not ok and "not enabled" not in detail and overall != "unhealthy":
        overall = "degraded"

    ok, detail = _check_render_worker()
    checks["render_worker"] = {"ok": ok, "detail": detail}
    if not ok:
        if render_worker_required:
            overall = "unhealthy"
        elif overall != "unhealthy":
            overall = "degraded"

    status_code = 200 if overall != "unhealthy" else 503
    resp = jsonify({
        "status": overall,
        "checks": checks,
        "debug_mode": Config.DEBUG,
        "render_worker_required": render_worker_required,
    })
    resp.headers["Cache-Control"] = "no-cache"
    return resp, status_code


@health_bp.route('/api/health')
@limiter.exempt
def health_check():
    """Backward-compatible health check — delegates to readiness."""
    return readiness()
