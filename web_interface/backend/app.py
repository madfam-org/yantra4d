"""
Tablaco Backend API
Production-ready Flask application for OpenSCAD rendering.

Structure:
- routes/render.py   - Render endpoints (estimate, render, render-stream)
- routes/health.py   - Health check endpoint
- routes/verify.py   - Verification endpoint
- services/openscad.py - OpenSCAD subprocess wrapper
- config.py          - Configuration management
"""
import logging
import os

from flask import Flask, send_from_directory
from flask_cors import CORS

from config import Config
from routes.render import render_bp
from routes.health import health_bp
from routes.verify import verify_bp

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if Config.DEBUG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_app():
    """Application factory for Flask app."""
    app = Flask(__name__)
    CORS(app)
    
    # Ensure static directory exists
    Config.STATIC_DIR.mkdir(parents=True, exist_ok=True)
    
    # Register blueprints
    app.register_blueprint(render_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(verify_bp)
    
    # Static file serving
    @app.route('/static/<path:filename>')
    def serve_static(filename):
        return send_from_directory(str(Config.STATIC_DIR), filename)
    
    logger.info(f"Tablaco Backend initialized - Debug: {Config.DEBUG}")
    logger.info(f"SCAD Directory: {Config.SCAD_DIR}")
    logger.info(f"OpenSCAD Path: {Config.OPENSCAD_PATH}")
    
    return app


# Create app instance for gunicorn
app = create_app()


if __name__ == '__main__':
    logger.info(f"Starting development server on port {Config.PORT}")
    app.run(debug=Config.DEBUG, port=Config.PORT, host=Config.HOST)
