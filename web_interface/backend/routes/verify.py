"""
Verify Blueprint
Handles /api/verify endpoint for design verification.
"""
import logging
import subprocess
import os

from flask import Blueprint, request, jsonify

from config import Config

logger = logging.getLogger(__name__)

verify_bp = Blueprint('verify', __name__)

STATIC_FOLDER = str(Config.STATIC_DIR)
PREVIEW_STL = str(Config.STATIC_DIR / "preview.stl")
VERIFY_SCRIPT = str(Config.VERIFY_SCRIPT)


@verify_bp.route('/api/verify', methods=['POST'])
def verify_design():
    """Run verification on the preview STL."""
    if not os.path.exists(PREVIEW_STL):
        return jsonify({"status": "error", "message": "No preview generated yet"}), 400
        
    cmd = ["python3", VERIFY_SCRIPT, PREVIEW_STL]
    logger.info(f"Verifying: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        success = result.returncode == 0
        return jsonify({
            "status": "success" if success else "failure",
            "output": result.stdout + "\n" + result.stderr,
            "passed": success
        })
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500
