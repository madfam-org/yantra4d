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
from routes.projects.datasheet import datasheet_bp
from routes.integrations.analytics import analytics_bp
from routes.users.user import user_bp
from routes.editor.github import github_bp
from routes.editor.editor import editor_bp
from routes.editor.git_ops import git_ops_bp
from routes.integrations.ai import ai_bp
from routes.projects.assembly import assembly_bp
from routes.integrations.storefront import storefront_bp
from routes.projects.catalog import catalog_bp
from routes.core.client_config import client_config_bp
from routes.projects.animations import animations_bp
from routes.integrations.printer import printer_bp
from routes.engine.analysis import analysis_bp
from routes.core.websocket import ws_bp, init_websocket
from services.core.mqtt_telemetry import telemetry_service

# Configure logging
from utils.logging_config import setup_logging
setup_logging(Config.DEBUG)
logger = logging.getLogger(__name__)


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
    app.register_blueprint(datasheet_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(github_bp)
    app.register_blueprint(editor_bp)
    app.register_blueprint(git_ops_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(assembly_bp)
    app.register_blueprint(storefront_bp)
    app.register_blueprint(catalog_bp)
    app.register_blueprint(client_config_bp)
    app.register_blueprint(animations_bp)
    app.register_blueprint(printer_bp)
    app.register_blueprint(analysis_bp)
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
