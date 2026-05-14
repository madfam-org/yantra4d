"""
Yantra4D Backend API
Production-ready Flask application for parametric 3D rendering.

Multi-engine render service (OpenSCAD, CadQuery, Implicit) with 24 blueprints
spanning: rendering, manifests, editor, AI, analytics, git ops, GitHub import,
project management, geometry analysis, printer integration, catalog, storefront,
health/readiness, and admin routes.

Key modules:
- config.py                   — AppConfig dataclass (env-driven)
- manifest.py                 — ManifestService singleton (project.json loader)
- services/engine/             — Render engines + orchestrator + cache
- services/ai/                 — LLM provider abstraction (Anthropic/OpenAI)
- services/editor/             — Editor CRUD + git ops + GitHub import
- middleware/auth.py           — JWT auth (Janua JWKS) + tier gating
"""
import atexit
import logging
import os
import shutil
from pathlib import Path
from urllib.parse import urlparse

from flask import Flask, g, jsonify, send_from_directory
from flask_cors import CORS

from config import Config
from extensions import limiter, db, migrate
from routes.engine.render import render_bp
from routes.core.health import health_bp
from routes.engine.verify import verify_bp
from routes.core.config_route import config_bp
from routes.core.manifest_route import manifest_bp
from routes.core.materials import materials_bp
from routes.projects.projects import projects_bp
from routes.users.onboard import onboard_bp
from routes.users.admin import admin_bp
from routes.engine.download import download_bp
from routes.projects.bom import bom_bp
from routes.projects.cart import cart_bp
from routes.projects.datasheet import datasheet_bp
from routes.integrations.analytics import analytics_bp
from routes.users.user import user_bp
from routes.editor.github import github_bp
from routes.editor.editor import editor_bp
from routes.editor.git_ops import git_ops_bp
from routes.integrations.ai import ai_bp
from routes.projects.assembly import assembly_bp
from routes.integrations.storefront import storefront_bp
from routes.integrations.pricing import pricing_bp
from routes.projects.catalog import catalog_bp
from routes.core.client_config import client_config_bp
from routes.projects.animations import animations_bp
from routes.integrations.printer import printer_bp
from routes.engine.analysis import analysis_bp
from routes.engine.simulate import simulate_bp
from routes.integrations.cotiza_export import cotiza_export_bp
from routes.integrations.cotiza_webhook import cotiza_webhook_bp
from routes.integrations.forgesight_webhook import forgesight_webhook_bp
from routes.core.websocket import ws_bp, init_websocket
from services.core.mqtt_telemetry import telemetry_service

# Configure logging
from utils.logging_config import setup_logging
setup_logging(Config.DEBUG)
logger = logging.getLogger(__name__)


def _check_capabilities():
    """Collect startup capability status for observability and non-fatal diagnostics."""
    capabilities = {}

    # OpenSCAD binary detection
    configured_path = Config.OPENSCAD_PATH
    resolved_openscad = configured_path if os.path.isabs(configured_path) else shutil.which(configured_path)
    if resolved_openscad and os.path.isfile(resolved_openscad) and os.access(resolved_openscad, os.X_OK):
        capabilities["openscad"] = {"status": "ok", "path": resolved_openscad}
    else:
        capabilities["openscad"] = {
            "status": "missing",
            "configured_path": configured_path,
            "resolved_path": resolved_openscad,
        }

    # Redis ping
    redis_url = Config.REDIS_URL
    try:
        import redis
        r = redis.Redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=1, socket_timeout=1)
        r.ping()
        capabilities["redis"] = {"status": "ok", "url": redis_url}
    except Exception as exc:
        capabilities["redis"] = {"status": "unavailable", "url": redis_url, "error": str(exc)}

    # Database URI sanity
    parsed_db = urlparse(Config.SQLALCHEMY_DATABASE_URI)
    if parsed_db.scheme == "sqlite":
        db_path = Path(parsed_db.path)
        if os.access(db_path.parent, os.R_OK | os.W_OK):
            db_status = "ok"
            db_error = None
        else:
            db_status = "path_inaccessible"
            db_error = f"Cannot access sqlite directory: {db_path.parent}"
    elif parsed_db.scheme and parsed_db.netloc:
        db_status = "ok"
        db_error = None
    else:
        db_status = "invalid"
        db_error = f"Unrecognized database URI: {Config.SQLALCHEMY_DATABASE_URI!r}"
    capabilities["database"] = {"status": db_status, "uri": Config.SQLALCHEMY_DATABASE_URI}
    if db_error:
        capabilities["database"]["error"] = db_error

    # Static path readiness
    static_path = Config.STATIC_DIR
    static_test = static_path / ".yantra_startup_write_test"
    if static_path.exists() and os.access(static_path, os.R_OK | os.W_OK):
        try:
            static_test.write_text("ok", encoding="utf-8")
            static_test.unlink()
            static_status = "ok"
            static_error = None
        except Exception as exc:
            static_status = "path_inaccessible"
            static_error = f"Static directory not writable: {exc}"
    else:
        static_status = "path_inaccessible"
        static_error = f"Static directory not readable/writable: {static_path}"

    capabilities["static_dir"] = {"status": static_status, "path": str(static_path)}
    if static_error:
        capabilities["static_dir"]["error"] = static_error

    # Optional AI credentials
    if Config.AI_API_KEY:
        capabilities["ai"] = {"status": "configured", "provider": Config.AI_PROVIDER}
    else:
        capabilities["ai"] = {"status": "disabled", "provider": Config.AI_PROVIDER, "note": "AI_API_KEY not configured"}

    return capabilities


def create_app():
    """Application factory for Flask app."""
    from posthog_analytics import init_posthog, shutdown as posthog_shutdown
    init_posthog()
    atexit.register(posthog_shutdown)

    app = Flask(__name__)
    app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB upload limit
    CORS(app, origins=Config.CORS_ORIGINS)

    limiter.init_app(app)

    # ── Observability ──────────────────────────────────────────────────
    # Sentry error tracking (no-op when SENTRY_DSN is unset)
    _sentry_dsn = os.environ.get("SENTRY_DSN")
    if _sentry_dsn:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.flask import FlaskIntegration
            sentry_sdk.init(dsn=_sentry_dsn, integrations=[FlaskIntegration()],
                            traces_sample_rate=float(os.environ.get("SENTRY_TRACES_RATE", "0.1")))
            logger.info("Sentry error tracking initialized")
        except ImportError:
            logger.info("sentry-sdk not installed; Sentry disabled")

    # Prometheus /metrics endpoint
    from utils.metrics import metrics_bp
    app.register_blueprint(metrics_bp)

    # OpenTelemetry distributed tracing (no-op when OTEL_EXPORTER_OTLP_ENDPOINT is unset)
    from utils.tracing import init_tracing
    init_tracing(app)

    # Database (PostgreSQL or SQLite fallback)
    app.config["SQLALCHEMY_DATABASE_URI"] = Config.SQLALCHEMY_DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    migrate.init_app(app, db)

    # Import models so Alembic can detect them
    import models  # noqa: F401

    from middleware.request_id import init_request_id
    init_request_id(app)

    # Ensure static directory exists
    Config.STATIC_DIR.mkdir(parents=True, exist_ok=True)

    # Register blueprints
    app.register_blueprint(render_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(verify_bp)
    app.register_blueprint(config_bp)
    app.register_blueprint(manifest_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(materials_bp)
    app.register_blueprint(onboard_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(download_bp)
    app.register_blueprint(bom_bp)
    app.register_blueprint(cart_bp)
    app.register_blueprint(datasheet_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(github_bp)
    app.register_blueprint(editor_bp)
    app.register_blueprint(git_ops_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(assembly_bp)
    app.register_blueprint(storefront_bp)
    app.register_blueprint(pricing_bp)
    app.register_blueprint(catalog_bp)
    app.register_blueprint(client_config_bp)
    app.register_blueprint(animations_bp)
    app.register_blueprint(printer_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(simulate_bp)
    app.register_blueprint(cotiza_export_bp)
    app.register_blueprint(cotiza_webhook_bp)
    app.register_blueprint(forgesight_webhook_bp)
    app.register_blueprint(ws_bp)

    # WebSocket support (additive — SSE endpoints untouched)
    init_websocket(app)

    # Static file serving
    @app.route('/static/<path:filename>')
    def serve_static(filename):
        resp = send_from_directory(str(Config.STATIC_DIR), filename)
        resp.headers["Cache-Control"] = "public, max-age=3600"
        return resp

    # Global error handlers — include request_id for traceability
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"status": "error", "error": "Bad request", "request_id": getattr(g, "request_id", None)}), 400

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"status": "error", "error": "Not found", "request_id": getattr(g, "request_id", None)}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"status": "error", "error": "Method not allowed", "request_id": getattr(g, "request_id", None)}), 405

    @app.errorhandler(413)
    def request_too_large(e):
        return jsonify({"status": "error", "error": "Request body too large", "request_id": getattr(g, "request_id", None)}), 413

    @app.errorhandler(429)
    def rate_limit_exceeded(e):
        return jsonify({"status": "error", "error": "Rate limit exceeded", "request_id": getattr(g, "request_id", None)}), 429

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({"status": "error", "error": "Internal server error", "request_id": getattr(g, "request_id", None)}), 500

    logger.info(f"Yantra4D Backend initialized - Debug: {Config.DEBUG}")
    logger.info(f"SCAD Directory: {Config.SCAD_DIR}")
    logger.info(f"Projects Directory: {Config.PROJECTS_DIR}")
    logger.info(f"Multi-project mode: {Config.MULTI_PROJECT}")
    logger.info(f"OpenSCAD Path: {Config.OPENSCAD_PATH}")
    startup_caps = _check_capabilities()
    logger.info("Startup capabilities: %s", startup_caps)
    app.config["STARTUP_CAPABILITIES"] = startup_caps
    for area, status in startup_caps.items():
        if status.get("status") not in ("ok", "configured"):
            logger.warning("Startup capability warning in %s: %s", area, status)

    # Start the continuous 4D Telemetry Bridge
    telemetry_service.start()

    # Start background render artifact garbage collection
    from services.engine.render_gc import start_gc
    start_gc()

    return app


# Create app instance for gunicorn
app = create_app()


if __name__ == '__main__':
    logger.info(f"Starting development server on port {Config.PORT}")
    app.run(debug=Config.DEBUG, port=Config.PORT, host=Config.HOST)
