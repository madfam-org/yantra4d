"""
Yantra4D Backend API
Production-ready Flask application for OpenSCAD rendering.

Structure:
- manifest.py          - Project manifest loader (modes, parts, parameters)
- config.py            - Environment configuration (paths, server settings)
- routes/render.py     - Render endpoints (estimate, render, render-stream, cancel)
- routes/verify.py     - Verification endpoint
- routes/health.py     - Health check endpoint
- routes/manifest_route.py - GET /api/manifest
- routes/config_route.py   - GET /api/config (legacy, delegates to manifest)
- services/openscad.py - OpenSCAD subprocess wrapper
"""
import logging
import os

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

from config import Config
from extensions import limiter
from routes.render import render_bp
from routes.health import health_bp
from routes.verify import verify_bp
from routes.config_route import config_bp
from routes.manifest_route import manifest_bp
from routes.projects import projects_bp
from routes.onboard import onboard_bp
from routes.admin import admin_bp
from routes.download import download_bp
from routes.bom import bom_bp
from routes.datasheet import datasheet_bp
from routes.analytics import analytics_bp
from routes.user import user_bp
from routes.github import github_bp
from routes.editor import editor_bp
from routes.git_ops import git_ops_bp
from routes.ai import ai_bp

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if Config.DEBUG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_app():
    """Application factory for Flask app."""
    app = Flask(__name__)
    app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB upload limit
    CORS(app, origins=[o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")])

    limiter.init_app(app)

    # Ensure static directory exists
    Config.STATIC_DIR.mkdir(parents=True, exist_ok=True)

    # Register blueprints
    app.register_blueprint(render_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(verify_bp)
    app.register_blueprint(config_bp)
    app.register_blueprint(manifest_bp)
    app.register_blueprint(projects_bp)
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

    # Static file serving
    @app.route('/static/<path:filename>')
    def serve_static(filename):
        resp = send_from_directory(str(Config.STATIC_DIR), filename)
        resp.headers["Cache-Control"] = "public, max-age=3600"
        return resp

    # Global error handlers
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"status": "error", "error": "Bad request"}), 400

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"status": "error", "error": "Not found"}), 404

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({"status": "error", "error": "Internal server error"}), 500

    logger.info(f"Yantra4D Backend initialized - Debug: {Config.DEBUG}")
    logger.info(f"SCAD Directory: {Config.SCAD_DIR}")
    logger.info(f"Projects Directory: {Config.PROJECTS_DIR}")
    logger.info(f"Multi-project mode: {Config.MULTI_PROJECT}")
    logger.info(f"OpenSCAD Path: {Config.OPENSCAD_PATH}")

    return app


# Create app instance for gunicorn
app = create_app()


if __name__ == '__main__':
    logger.info(f"Starting development server on port {Config.PORT}")
    app.run(debug=Config.DEBUG, port=Config.PORT, host=Config.HOST)
