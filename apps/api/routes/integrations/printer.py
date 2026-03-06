"""
apps/api/routes/integrations/printer.py

Printer Integration Blueprint — OctoPrint / Moonraker dispatch.

Endpoints:
  GET  /api/printers                   — list configured printers
  GET  /api/printers/<id>/status       — proxy status from printer API
  POST /api/printers/<id>/print        — upload + start print (pro+ tier)
  DELETE /api/printers/<id>/print      — cancel active job
"""

import json
import logging
import os
import re
from pathlib import Path

from flask import Blueprint, jsonify, request

from middleware.auth import require_tier
from utils.route_helpers import error_response, handle_exceptions, safe_join_path

logger = logging.getLogger(__name__)
printer_bp = Blueprint("printer", __name__)

PRINTERS_DIR = Path(os.getenv("PRINTERS_DIR", str(Path(__file__).parents[4] / "printers")))

# Printer ID: lowercase alphanumeric, hyphens, underscores. 3-50 chars.
_PRINTER_ID_RE = re.compile(r'^[a-z0-9][a-z0-9_-]{1,48}[a-z0-9]$')


def _validate_printer_id(printer_id: str) -> str | None:
    """Validate a printer ID. Returns error message or None if valid."""
    if not printer_id or not _PRINTER_ID_RE.match(printer_id):
        return "Invalid printer_id: must be 3-50 lowercase alphanumeric characters, hyphens, or underscores"
    return None


def _load_printer(printer_id: str) -> dict | None:
    """Load a printer.json by ID (filename without .json)."""
    path = safe_join_path(str(PRINTERS_DIR), f"{printer_id}.json")
    if path is None or not path.is_file():
        return None
    try:
        with open(path) as f:
            data = json.load(f)
        data["id"] = printer_id
        return data
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load printer '%s': %s", printer_id, e)
        return None


def _get_client(printer: dict):
    """Return the correct service module for this printer's connection type."""
    conn_type = printer.get("connection", {}).get("type", "octoprint")
    if conn_type == "moonraker":
        from services.integrations import moonraker as client
    else:
        from services.integrations import octoprint as client
    return client


@printer_bp.route("/api/printers", methods=["GET"])
@require_tier("pro")
@handle_exceptions
def list_printers():
    """Return all configured printers (name, model, connection type, id)."""
    if not PRINTERS_DIR.is_dir():
        return jsonify({"printers": []})

    printers = []
    for path in sorted(PRINTERS_DIR.glob("*.json")):
        if path.name.startswith("example-"):
            continue  # skip the bundled example
        try:
            with open(path) as f:
                data = json.load(f)
            hw = data.get("hardware", {})
            conn = data.get("connection", {})
            printers.append({
                "id": path.stem,
                "name": hw.get("name", path.stem),
                "brand": hw.get("brand", ""),
                "model": hw.get("model", ""),
                "connection_type": conn.get("type", "octoprint"),
                "bed_size_mm": [
                    hw.get("bed_x_mm"),
                    hw.get("bed_y_mm"),
                    hw.get("bed_z_mm"),
                ],
            })
        except Exception as e:
            logger.warning("Skipping invalid printer config %s: %s", path.name, e)

    return jsonify({"printers": printers})


@printer_bp.route("/api/printers/<printer_id>/status", methods=["GET"])
@require_tier("pro")
@handle_exceptions
def get_printer_status(printer_id: str):
    """Proxy real-time status from the printer's API."""
    err = _validate_printer_id(printer_id)
    if err:
        return error_response(err, 400)
    printer = _load_printer(printer_id)
    if printer is None:
        return error_response(f"Printer '{printer_id}' not found.", 404)

    conn = printer["connection"]
    client = _get_client(printer)

    status = client.get_status(conn["base_url"], conn.get("api_key", ""))
    return jsonify({
        "printer_id": printer_id,
        "name": printer.get("hardware", {}).get("name", printer_id),
        **status,
    })


@printer_bp.route("/api/printers/<printer_id>/print", methods=["POST"])
@require_tier("pro")
@handle_exceptions
def dispatch_print(printer_id: str):
    """
    Upload a rendered file to the printer and start the print job.

    Tier-gated: requires 'pro' or above.
    Request body: { "file_path": "output.stl" }
    """
    err = _validate_printer_id(printer_id)
    if err:
        return error_response(err, 400)

    printer = _load_printer(printer_id)
    if printer is None:
        return error_response(f"Printer '{printer_id}' not found.", 404)

    data = request.get_json(silent=True) or {}
    file_path = data.get("file_path", "")
    if not file_path:
        return error_response("Missing 'file_path' in request body.", 400)

    # Sanitize file_path: must resolve inside STATIC_DIR
    from config import Config
    safe_path = safe_join_path(str(Config.STATIC_DIR), Path(file_path).name)
    if safe_path is None or not safe_path.is_file():
        return error_response("Invalid or inaccessible file path.", 400)
    file_path = str(safe_path)

    conn = printer["connection"]
    client = _get_client(printer)

    try:
        remote_name = client.upload_file(conn["base_url"], conn.get("api_key", ""), file_path)
        client.start_print(conn["base_url"], conn.get("api_key", ""), remote_name)
        return jsonify({
            "status": "printing",
            "printer_id": printer_id,
            "remote_file": remote_name,
        })
    except RuntimeError as e:
        return error_response(str(e), 502)


@printer_bp.route("/api/printers/<printer_id>/print", methods=["DELETE"])
@require_tier("pro")
@handle_exceptions
def cancel_print_job(printer_id: str):
    """Cancel the active print job on the specified printer."""
    err = _validate_printer_id(printer_id)
    if err:
        return error_response(err, 400)

    printer = _load_printer(printer_id)
    if printer is None:
        return error_response(f"Printer '{printer_id}' not found.", 404)

    conn = printer["connection"]
    client = _get_client(printer)

    try:
        client.cancel_print(conn["base_url"], conn.get("api_key", ""))
        return jsonify({"status": "cancelled", "printer_id": printer_id})
    except RuntimeError as e:
        return error_response(str(e), 502)
