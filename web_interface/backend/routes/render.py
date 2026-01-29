"""
Render Blueprint
Handles /api/estimate, /api/render, /api/render-stream endpoints.
"""
import logging
import os
import json

from flask import Blueprint, request, jsonify, Response

from config import Config
from manifest import get_manifest
from services.openscad import build_openscad_command, run_render, stream_render, cancel_render

logger = logging.getLogger(__name__)

render_bp = Blueprint('render', __name__)

STATIC_FOLDER = str(Config.STATIC_DIR)


def _resolve_render_context(data):
    """Resolve scad_file, parts, and mode_map from payload.

    Supports both new `mode` field and legacy `scad_file` field.
    """
    manifest = get_manifest()
    mode_id = data.get('mode')
    scad_filename = data.get('scad_file')

    if mode_id:
        scad_filename = manifest.get_scad_file_for_mode(mode_id)
        parts = manifest.get_parts_for_mode(mode_id)
    else:
        if not scad_filename:
            scad_filename = 'half_cube.scad'
        parts_map = manifest.get_parts_map()
        parts = parts_map.get(scad_filename, ["main"])

    allowed = manifest.get_allowed_files()
    if scad_filename not in allowed:
        return None, None, None, scad_filename

    scad_path = str(allowed[scad_filename])
    mode_map = manifest.get_mode_map()
    return scad_filename, scad_path, parts, mode_map


@render_bp.route('/api/estimate', methods=['POST'])
def estimate_render_time():
    """Estimate render time based on parameters before actually rendering."""
    data = request.json
    manifest = get_manifest()
    constants = manifest.estimate_constants

    mode_id = data.get('mode')
    scad_file = data.get('scad_file')

    # Resolve mode_id from scad_file for backward compat
    if not mode_id and scad_file:
        for m in manifest.modes:
            if m["scad_file"] == scad_file:
                mode_id = m["id"]
                break
    if not mode_id:
        mode_id = manifest.modes[0]["id"]

    num_units = manifest.calculate_estimate_units(mode_id, data)
    num_parts = len(manifest.get_parts_for_mode(mode_id))

    est = (constants["base_time"] +
           num_units * constants["per_unit"] +
           num_parts * constants["per_part"])

    return jsonify({
        "estimated_seconds": round(est, 1),
        "num_parts": num_parts,
        "num_units": num_units
    })


@render_bp.route('/api/render', methods=['POST'])
def render_stl():
    """Synchronous render endpoint."""
    data = request.json
    scad_filename, scad_path, parts_to_render, mode_map = _resolve_render_context(data)

    if scad_filename is None:
        bad_name = scad_path  # 4th return is the bad filename on error
        return jsonify({"status": "error", "error": f"Invalid SCAD file: {bad_name}"}), 400

    generated_parts = []
    combined_log = ""

    try:
        for part in parts_to_render:
            output_filename = f"preview_{part}.stl"
            output_path = os.path.join(STATIC_FOLDER, output_filename)

            render_mode = mode_map.get(part, 0)
            params = data.get('parameters', data)
            cmd = build_openscad_command(output_path, scad_path, params, render_mode)

            success, stderr = run_render(cmd)
            if not success:
                return jsonify({"status": "error", "error": stderr}), 500

            combined_log += f"[{part}] {stderr}\n"
            size_bytes = os.path.getsize(output_path) if os.path.exists(output_path) else None
            generated_parts.append({
                "type": part,
                "url": f"{request.host_url}static/{output_filename}",
                "size_bytes": size_bytes
            })

        return jsonify({
            "status": "success",
            "parts": generated_parts,
            "log": combined_log
        })
    except Exception as e:
        logger.error(f"Render failed: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500


@render_bp.route('/api/render-stream', methods=['POST'])
def render_stl_stream():
    """Stream render progress via Server-Sent Events (SSE)."""
    data = request.json
    scad_filename, scad_path, parts_to_render, mode_map = _resolve_render_context(data)

    if scad_filename is None:
        bad_name = scad_path
        def error_gen():
            yield f"data: {json.dumps({'error': f'Invalid SCAD file: {bad_name}'})}\n\n"
        return Response(error_gen(), mimetype='text/event-stream')

    num_parts = len(parts_to_render)
    host_url = request.host_url
    params = data.get('parameters', data)

    def generate():
        generated_parts = []

        for i, part in enumerate(parts_to_render):
            output_filename = f"preview_{part}.stl"
            output_path = os.path.join(STATIC_FOLDER, output_filename)

            part_base = (i / num_parts) * 100
            part_weight = 100 / num_parts

            render_mode = mode_map.get(part, 0)
            cmd = build_openscad_command(output_path, scad_path, params, render_mode)

            for event_data in stream_render(cmd, part, part_base, part_weight, i, num_parts):
                yield f"data: {event_data}\n\n"
                event = json.loads(event_data)
                if event.get('event') == 'part_done':
                    size_bytes = os.path.getsize(output_path) if os.path.exists(output_path) else None
                    generated_parts.append({
                        "type": part,
                        "url": f"{host_url}static/{output_filename}",
                        "size_bytes": size_bytes
                    })

        yield f"data: {json.dumps({'event': 'complete', 'parts': generated_parts, 'progress': 100})}\n\n"

    return Response(generate(), mimetype='text/event-stream')


@render_bp.route('/api/render-cancel', methods=['POST'])
def cancel_render_endpoint():
    """Cancel the active render process."""
    cancelled = cancel_render()
    return jsonify({
        "status": "cancelled" if cancelled else "no_active_render",
        "cancelled": cancelled
    })
