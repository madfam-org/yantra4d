"""
OpenSCAD Service
Handles all OpenSCAD subprocess interactions.
"""
import logging
import os
import re
import subprocess
import json
import threading

from config import Config
from manifest import get_manifest

logger = logging.getLogger(__name__)

RENDER_TIMEOUT_S = 300


def _openscad_env():
    """Return environment with OPENSCADPATH set for library resolution."""
    env = os.environ.copy()
    env["OPENSCADPATH"] = Config.OPENSCADPATH
    return env

# Track the active render process for cancellation
_active_process = None
_process_lock = threading.Lock()

# Phase weights represent the approximate % of total render time each OpenSCAD
# phase consumes. Used to calculate progress bar position during streaming renders.
PHASE_WEIGHTS = {
    'start': 5,
    'compiling': 15,
    'geometry': 25,
    'cgal': 35,
    'rendering': 15,
    'done': 5
}

PHASE_ORDER = ['start', 'compiling', 'geometry', 'cgal', 'rendering', 'done']


def get_phase_from_line(line: str) -> str | None:
    """Detect OpenSCAD phase from output line."""
    line_lower = line.lower()
    if 'compiling design' in line_lower or 'parsing design' in line_lower:
        return 'compiling'
    elif 'geometries in cache' in line_lower or 'geometry cache' in line_lower:
        return 'geometry'
    elif 'cgal' in line_lower:
        return 'cgal'
    elif 'rendering' in line_lower or 'total rendering time' in line_lower:
        return 'rendering'
    elif 'simple:' in line_lower or 'vertices:' in line_lower:
        return 'done'
    return None


def validate_params(params: dict, project_slug: str | None = None) -> dict:
    """Validate parameters against the manifest.

    Checks types, enforces min/max for numbers, and rejects unknown keys.
    Returns a cleaned dict of validated parameters.
    """
    manifest = get_manifest(project_slug)
    param_defs = {p["id"]: p for p in manifest.parameters}
    pass_through_keys = {"mode", "scad_file", "parameters"}
    cleaned = {}

    for key, value in params.items():
        if key in pass_through_keys:
            continue

        if key not in param_defs:
            logger.warning(f"Rejecting unknown parameter: {key}")
            continue

        defn = param_defs[key]
        param_type = defn.get("type", "slider")

        if param_type == "slider":
            try:
                num_val = float(value)
            except (TypeError, ValueError):
                logger.warning(f"Rejecting non-numeric value for {key}: {value}")
                continue
            min_val = defn.get("min")
            max_val = defn.get("max")
            if min_val is not None and num_val < float(min_val):
                num_val = float(min_val)
            if max_val is not None and num_val > float(max_val):
                num_val = float(max_val)
            cleaned[key] = num_val
        elif param_type == "text":
            str_val = str(value)
            if not re.match(r'^[a-zA-Z0-9 _.-]*$', str_val):
                logger.warning(f"Rejecting unsafe text value for {key}")
                continue
            maxlen = defn.get("maxlength", 255)
            if len(str_val) > maxlen:
                str_val = str_val[:maxlen]
            cleaned[key] = str_val
        elif param_type == "checkbox":
            if isinstance(value, bool):
                cleaned[key] = value
            elif str(value).lower() in ("true", "false"):
                cleaned[key] = str(value).lower() == "true"
            else:
                logger.warning(f"Rejecting non-boolean value for {key}: {value}")
                continue
        else:
            str_val = str(value)
            if not re.match(r'^[a-zA-Z0-9_]+$', str_val):
                logger.warning(f"Rejecting non-alphanumeric string for {key}: {value}")
                continue
            cleaned[key] = str_val

    return cleaned


def build_openscad_command(output_path: str, scad_path: str, params: dict, mode_id: int = 0) -> list:
    """Build OpenSCAD command with parameters."""
    cmd = [Config.OPENSCAD_PATH, "-o", output_path]

    for key, value in params.items():
        if key == 'scad_file':
            continue
        if isinstance(value, bool):
            val_str = str(value).lower()
        elif isinstance(value, (int, float)):
            val_str = str(value)
        elif isinstance(value, str):
            val_str = f'"{value}"'
        else:
            str_val = str(value)
            if re.match(r'^[a-zA-Z0-9_]+$', str_val):
                val_str = str_val
            else:
                try:
                    float(str_val)
                    val_str = str_val
                except (TypeError, ValueError):
                    if str_val.lower() in ("true", "false"):
                        val_str = str_val.lower()
                    else:
                        logger.warning(f"Skipping invalid -D value for {key}: {str_val}")
                        continue
        cmd.extend(["-D", f"{key}={val_str}"])

    if mode_id != 0:
        cmd.extend(["-D", f"render_mode={mode_id}"])

    cmd.append(scad_path)
    return cmd


def _sanitize_cmd_for_log(cmd: list) -> str:
    """Redact -D parameter values from command for safe logging."""
    sanitized = []
    skip_next = False
    for i, arg in enumerate(cmd):
        if skip_next:
            # Redact the value part after '=' in -D args
            if "=" in arg:
                key = arg.split("=", 1)[0]
                sanitized.append(f"{key}=<redacted>")
            else:
                sanitized.append("<redacted>")
            skip_next = False
        elif arg == "-D":
            sanitized.append(arg)
            skip_next = True
        else:
            sanitized.append(arg)
    return " ".join(sanitized)


def run_render(cmd: list) -> tuple[bool, str]:
    """Execute OpenSCAD render synchronously. Returns (success, stderr)."""
    logger.info(f"Running OpenSCAD: {_sanitize_cmd_for_log(cmd)}")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=RENDER_TIMEOUT_S, env=_openscad_env())
        return True, result.stderr
    except subprocess.TimeoutExpired:
        logger.error("OpenSCAD render timed out after %ds", RENDER_TIMEOUT_S)
        return False, f"Render timed out after {RENDER_TIMEOUT_S} seconds"
    except subprocess.CalledProcessError as e:
        logger.error(f"OpenSCAD failed: {e.stderr}")
        return False, e.stderr


def stream_render(cmd: list, part: str, part_base: float, part_weight: float, index: int, total: int):
    """
    Generator that streams OpenSCAD progress as SSE events.
    Yields JSON-formatted SSE data strings.
    """
    current_phase_progress = PHASE_WEIGHTS['start']
    
    # Send part start event
    initial_progress = part_base + (PHASE_WEIGHTS['start'] / 100) * part_weight
    yield json.dumps({
        'event': 'part_start', 
        'part': part, 
        'progress': round(initial_progress),
        'index': index,
        'total': total
    })
    
    # Run with Popen to stream stderr
    global _active_process
    process = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True, env=_openscad_env())
    with _process_lock:
        _active_process = process

    kill_timer = threading.Timer(RENDER_TIMEOUT_S, lambda: process.kill())
    kill_timer.start()

    try:
        for line in process.stderr:
            line = line.strip()
            if not line:
                continue

            # Detect phase transitions
            detected_phase = get_phase_from_line(line)
            if detected_phase and detected_phase in PHASE_ORDER:
                phase_idx = PHASE_ORDER.index(detected_phase)
                current_phase_progress = sum(PHASE_WEIGHTS.get(p, 0) for p in PHASE_ORDER[:phase_idx + 1])

            # Calculate overall progress
            overall_progress = part_base + (current_phase_progress / 100) * part_weight

            yield json.dumps({
                'event': 'output',
                'part': part,
                'line': line,
                'progress': round(overall_progress)
            })

        process.wait()
    finally:
        kill_timer.cancel()
        with _process_lock:
            _active_process = None

    if process.returncode == 0:
        final_progress = part_base + part_weight
        yield json.dumps({
            'event': 'part_done', 
            'part': part, 
            'progress': round(final_progress)
        })
        return True
    else:
        yield json.dumps({
            'event': 'error',
            'part': part,
            'message': 'Render failed'
        })
        return False


def cancel_render():
    """Kill the active OpenSCAD render process if one is running."""
    global _active_process
    with _process_lock:
        if _active_process and _active_process.poll() is None:
            logger.info("Cancelling active render process")
            _active_process.terminate()
            try:
                _active_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                _active_process.kill()
            _active_process = None
            return True
    return False
