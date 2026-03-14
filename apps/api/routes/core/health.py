"""
Health Blueprint
Provides /api/health, /api/health/live, and /api/health/ready endpoints.
"""
import logging
import os
import resource
import shutil

from flask import Blueprint, jsonify

from config import Config
from extensions import limiter

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
    """Check analytics DB is writable."""
    db_path = Config.ANALYTICS_DB_PATH
    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        # Test write by touching the parent dir
        if db_path.exists():
            return os.access(db_path, os.W_OK), "writable" if os.access(db_path, os.W_OK) else "read-only"
        # DB doesn't exist yet — check parent is writable
        return os.access(db_path.parent, os.W_OK), "parent writable"
    except Exception as e:
        return False, str(e)


def _check_disk_space() -> tuple[bool, str]:
    """Check available disk space on STATIC_DIR."""
    try:
        usage = shutil.disk_usage(str(Config.STATIC_DIR))
        free_mb = usage.free / (1024 * 1024)
        pct_free = (usage.free / usage.total) * 100
        ok = free_mb > 100  # At least 100MB free
        return ok, f"{free_mb:.0f}MB free ({pct_free:.1f}%)"
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

    # Optional: OpenSCAD (platform supports WASM fallback)
    ok, detail = _check_openscad()
    checks["openscad"] = {"ok": ok, "detail": detail}
    if not ok:
        if overall != "unhealthy":
            overall = "degraded"

    # Optional: Redis
    ok, detail = _check_redis()
    checks["redis"] = {"ok": ok, "detail": detail}
    if not ok and "not configured" not in detail:
        if overall != "unhealthy":
            overall = "degraded"

    # Optional: Analytics DB
    ok, detail = _check_analytics_db()
    checks["analytics_db"] = {"ok": ok, "detail": detail}
    if not ok:
        if overall != "unhealthy":
            overall = "degraded"

    # Optional: Disk space
    ok, detail = _check_disk_space()
    checks["disk"] = {"ok": ok, "detail": detail}
    if not ok:
        if overall != "unhealthy":
            overall = "degraded"

    # Optional: Memory
    ok, detail = _check_memory()
    checks["memory"] = {"ok": ok, "detail": detail}
    if not ok:
        if overall != "unhealthy":
            overall = "degraded"

    status_code = 200 if overall != "unhealthy" else 503
    resp = jsonify({
        "status": overall,
        "checks": checks,
        "debug_mode": Config.DEBUG,
    })
    resp.headers["Cache-Control"] = "no-cache"
    return resp, status_code


@health_bp.route('/api/health')
@limiter.exempt
def health_check():
    """Backward-compatible health check — delegates to readiness."""
    return readiness()
