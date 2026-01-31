"""
Verify Blueprint
Handles /api/verify endpoint for design verification.
"""
import json
import logging
import subprocess
import sys

from flask import Blueprint, request, jsonify

from config import Config
from extensions import limiter
from manifest import get_manifest, resolve_part_config
from middleware.auth import require_auth
from services.route_helpers import safe_join_path

logger = logging.getLogger(__name__)

verify_bp = Blueprint('verify', __name__)

STATIC_FOLDER = str(Config.STATIC_DIR)
VERIFY_SCRIPT = str(Config.VERIFY_SCRIPT)


@verify_bp.route('/api/verify', methods=['POST'])
@require_auth
@limiter.limit("50/hour")
def verify_design():
    """Run verification on rendered STL parts for the current mode."""
    data = request.json or {}
    project_slug = data.get('project')
    manifest = get_manifest(project_slug)
    mode = data.get('mode', manifest.modes[0]["id"])

    parts = manifest.get_parts_for_mode(mode)
    if not parts:
        parts = manifest.get_parts_for_mode(manifest.modes[0]["id"])

    # Build verification config from manifest
    verify_cfg = manifest.get_verification_config(mode)

    stl_prefix = f"{project_slug}_{Config.STL_PREFIX}" if project_slug else Config.STL_PREFIX

    results = []
    all_passed = True

    for part in parts:
        stl_filename = f"{stl_prefix}{part}.stl"
        resolved = safe_join_path(STATIC_FOLDER, stl_filename)

        if resolved is None:
            results.append(f"--- {part} ---\n[ERROR] Invalid path\n")
            all_passed = False
            continue

        if not resolved.exists():
            results.append(f"--- {part} ---\n[SKIP] File not found: {stl_filename}\n")
            all_passed = False
            continue

        # Build part-specific config
        if verify_cfg is not None:
            part_cfg = resolve_part_config(verify_cfg, part)
            cmd = [sys.executable, VERIFY_SCRIPT, str(resolved), json.dumps(part_cfg)]
        else:
            cmd = [sys.executable, VERIFY_SCRIPT, str(resolved)]

        logger.info(f"Verifying {part}: {' '.join(cmd[:3])}...")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            output = result.stdout + result.stderr

            # Parse structured output (look for ===JSON=== marker)
            if "===JSON===" in output:
                text_output, json_str = output.split("===JSON===", 1)
                try:
                    structured = json.loads(json_str.strip())
                except json.JSONDecodeError:
                    structured = {"passed": result.returncode == 0}
            else:
                text_output = output
                structured = {"passed": result.returncode == 0}

            results.append(f"--- {part} ---\n{text_output.strip()}")
            if not structured.get("passed", False):
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
