"""
Verify Blueprint
Handles /api/verify endpoint for design verification.
"""
import logging
import subprocess
import sys

from flask import Blueprint, request, jsonify

from config import Config
from manifest import get_manifest
from services.route_helpers import safe_join_path

logger = logging.getLogger(__name__)

verify_bp = Blueprint('verify', __name__)

STATIC_FOLDER = str(Config.STATIC_DIR)
VERIFY_SCRIPT = str(Config.VERIFY_SCRIPT)


@verify_bp.route('/api/verify', methods=['POST'])
def verify_design():
    """Run verification on rendered STL parts for the current mode."""
    data = request.json or {}
    manifest = get_manifest()
    mode = data.get('mode', manifest.modes[0]["id"])

    parts = manifest.get_parts_for_mode(mode)
    if not parts:
        parts = manifest.get_parts_for_mode(manifest.modes[0]["id"])

    results = []
    all_passed = True

    for part in parts:
        stl_filename = f"{Config.STL_PREFIX}{part}.stl"
        resolved = safe_join_path(STATIC_FOLDER, stl_filename)

        if resolved is None:
            results.append(f"--- {part} ---\n[ERROR] Invalid path\n")
            all_passed = False
            continue

        if not resolved.exists():
            results.append(f"--- {part} ---\n[SKIP] File not found: {stl_filename}\n")
            all_passed = False
            continue

        cmd = [sys.executable, VERIFY_SCRIPT, str(resolved)]
        logger.info(f"Verifying {part}: {' '.join(cmd)}")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            output = result.stdout + result.stderr
            results.append(f"--- {part} ---\n{output}")
            if result.returncode != 0:
                all_passed = False
        except subprocess.TimeoutExpired:
            logger.error(f"Verification timed out for {part}")
            results.append(f"--- {part} ---\n[ERROR] Verification timed out\n")
            all_passed = False
        except Exception as e:
            logger.error(f"Verification failed for {part}: {e}")
            results.append(f"--- {part} ---\n[ERROR] {str(e)}\n")
            all_passed = False

    combined = "\n".join(results)
    return jsonify({
        "status": "success" if all_passed else "failure",
        "output": combined,
        "passed": all_passed,
        "parts_checked": len(parts)
    })
