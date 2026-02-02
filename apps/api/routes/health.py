"""
Health Blueprint
Provides /api/health endpoint for monitoring.
"""
import os

from flask import Blueprint, jsonify

from config import Config

health_bp = Blueprint('health', __name__)


@health_bp.route('/api/health')
def health_check():
    """Health check endpoint for monitoring and load balancers."""
    openscad_available = os.path.exists(Config.OPENSCAD_PATH)
    resp = jsonify({
        "status": "healthy",
        "openscad_available": openscad_available,
        "debug_mode": Config.DEBUG
    })
    resp.headers["Cache-Control"] = "no-cache"
    return resp
