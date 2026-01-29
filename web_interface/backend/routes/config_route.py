"""
Config Blueprint
Exposes dynamic configuration to the frontend.
"""
from flask import Blueprint, jsonify
from config import Config

config_bp = Blueprint('config', __name__)


@config_bp.route('/api/config', methods=['GET'])
def get_config():
    """Return dynamic configuration for the frontend."""
    return jsonify({
        "parts_map": {k: list(v) for k, v in Config.PARTS_MAP.items()},
        "mode_map": dict(Config.MODE_MAP),
        "estimate_constants": dict(Config.ESTIMATE_CONSTANTS),
    })
