"""
Render Blueprint
Handles /api/estimate, /api/render, /api/render-stream endpoints.
"""
import logging
import os
import json

from flask import Blueprint, request, jsonify, Response

from config import Config
from services.openscad import build_openscad_command, run_render, stream_render

logger = logging.getLogger(__name__)

render_bp = Blueprint('render', __name__)

# Convenience aliases
ALLOWED_FILES = {k: str(v) for k, v in Config.ALLOWED_FILES.items()}
PARTS_MAP = Config.PARTS_MAP
MODE_MAP = Config.MODE_MAP
ESTIMATE_CONSTANTS = Config.ESTIMATE_CONSTANTS
STATIC_FOLDER = str(Config.STATIC_DIR)


@render_bp.route('/api/estimate', methods=['POST'])
def estimate_render_time():
    """Estimate render time based on parameters before actually rendering."""
    data = request.json
    scad_file = data.get('scad_file', 'half_cube.scad')
    rows = data.get('rows', 1)
    cols = data.get('cols', 1)
    
    num_parts = len(PARTS_MAP.get(scad_file, ["main"]))
    
    if scad_file == 'tablaco.scad':
        num_units = rows * cols
    elif scad_file == 'assembly.scad':
        num_units = 2
    else:
        num_units = 1
    
    est = (ESTIMATE_CONSTANTS["base_time"] +
           num_units * ESTIMATE_CONSTANTS["per_unit"] +
           num_parts * ESTIMATE_CONSTANTS["per_part"])
    
    return jsonify({
        "estimated_seconds": round(est, 1),
        "num_parts": num_parts,
        "num_units": num_units
    })


@render_bp.route('/api/render', methods=['POST'])
def render_stl():
    """Synchronous render endpoint."""
    data = request.json
    scad_filename = data.get('scad_file', 'half_cube.scad')
    
    if scad_filename not in ALLOWED_FILES:
        return jsonify({"status": "error", "error": f"Invalid SCAD file: {scad_filename}"}), 400
        
    scad_path = ALLOWED_FILES[scad_filename]
    parts_to_render = PARTS_MAP.get(scad_filename, ["main"])
    
    generated_parts = []
    combined_log = ""
    
    try:
        for part in parts_to_render:
            output_filename = f"preview_{part}.stl"
            output_path = os.path.join(STATIC_FOLDER, output_filename)
            
            mode_id = MODE_MAP.get(part, 0)
            cmd = build_openscad_command(output_path, scad_path, data, mode_id)
            
            success, stderr = run_render(cmd)
            if not success:
                return jsonify({"status": "error", "error": stderr}), 500
            
            combined_log += f"[{part}] {stderr}\n"
            generated_parts.append({
                "type": part,
                "url": f"http://localhost:5000/static/{output_filename}"
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
    scad_filename = data.get('scad_file', 'half_cube.scad')
    
    if scad_filename not in ALLOWED_FILES:
        def error_gen():
            yield f"data: {json.dumps({'error': f'Invalid SCAD file: {scad_filename}'})}\n\n"
        return Response(error_gen(), mimetype='text/event-stream')
    
    scad_path = ALLOWED_FILES[scad_filename]
    parts_to_render = PARTS_MAP.get(scad_filename, ["main"])
    num_parts = len(parts_to_render)
    
    def generate():
        generated_parts = []
        
        for i, part in enumerate(parts_to_render):
            output_filename = f"preview_{part}.stl"
            output_path = os.path.join(STATIC_FOLDER, output_filename)
            
            part_base = (i / num_parts) * 100
            part_weight = 100 / num_parts
            
            mode_id = MODE_MAP.get(part, 0)
            cmd = build_openscad_command(output_path, scad_path, data, mode_id)
            
            # Stream progress events
            for event_data in stream_render(cmd, part, part_base, part_weight, i, num_parts):
                yield f"data: {event_data}\n\n"
                event = json.loads(event_data)
                if event.get('event') == 'part_done':
                    generated_parts.append({
                        "type": part,
                        "url": f"http://localhost:5000/static/{output_filename}"
                    })
        
        # Final completion event
        yield f"data: {json.dumps({'event': 'complete', 'parts': generated_parts, 'progress': 100})}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')
