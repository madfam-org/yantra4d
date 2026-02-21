"""
OpenSCAD Service
Handles all OpenSCAD subprocess interactions.
"""
import logging
import os
import re
import subprocess
import json
import tempfile
import threading
from pathlib import Path

from config import Config
from manifest import get_manifest
from services.render_engine import RENDER_TIMEOUT_S, ProcessManager

logger = logging.getLogger(__name__)

# Cache fontconfig temp files per project fonts dir so they're created once
_fontconfig_cache: dict[str, str] = {}


def _openscad_env(scad_path: str | None = None):
    """Return environment with OPENSCADPATH and optional font config set.

    When *scad_path* is provided, its parent directory is prepended to
    OPENSCADPATH. If the directory contains a ``fonts/`` subdirectory,
    a minimal fontconfig configuration is generated.
    """
    env = os.environ.copy()
    paths = [Config.OPENSCADPATH]

    if scad_path:
        project_dir = str(Path(scad_path).parent)
        paths.insert(0, project_dir)
        
        fonts_dir = os.path.join(project_dir, "fonts")
        if os.path.isdir(fonts_dir):
            if fonts_dir not in _fontconfig_cache:
                fd, conf_path = tempfile.mkstemp(suffix=".conf", prefix="fc_yantra_")
                os.write(fd, (
                    '<?xml version="1.0"?>\n'
                    '<!DOCTYPE fontconfig SYSTEM "fonts.dtd">\n'
                    '<fontconfig>\n'
                    f'  <dir>{fonts_dir}</dir>\n'
                    '  <include ignore_missing="yes">/etc/fonts/fonts.conf</include>\n'
                    '</fontconfig>\n'
                ).encode())
                os.close(fd)
                _fontconfig_cache[fonts_dir] = conf_path
                logger.info("Created fontconfig for %s → %s", fonts_dir, conf_path)
            env["FONTCONFIG_FILE"] = _fontconfig_cache[fonts_dir]

    env["OPENSCADPATH"] = os.pathsep.join(paths)
    return env

# Per-engine process manager for cancellation support
_process_manager = ProcessManager()

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

    # Explicitly remove render_mode if present, as it's handled via the mode ID
    if 'render_mode' in cleaned:
        del cleaned['render_mode']

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


def run_render(cmd: list, scad_path: str | None = None) -> tuple[bool, str]:
    """Execute OpenSCAD render synchronously. Returns (success, stderr)."""
    logger.info(f"Running OpenSCAD: {_sanitize_cmd_for_log(cmd)}")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=RENDER_TIMEOUT_S, env=_openscad_env(scad_path))
        return True, result.stderr
    except subprocess.TimeoutExpired:
        logger.error("OpenSCAD render timed out after %ds", RENDER_TIMEOUT_S)
        return False, f"Render timed out after {RENDER_TIMEOUT_S} seconds"
    except subprocess.CalledProcessError as e:
        logger.error(f"OpenSCAD failed: {e.stderr}")
        return False, e.stderr


def stream_render(cmd: list, part: str, part_base: float, part_weight: float, index: int, total: int, scad_path: str | None = None):
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

    try:
        # Run with Popen to stream stderr
        logger.info(f"Streaming OpenSCAD (CWD: {os.getcwd()}): {_sanitize_cmd_for_log(cmd)}")
        process = _process_manager.start(
            subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True, env=_openscad_env(scad_path))
        )

        kill_timer = threading.Timer(RENDER_TIMEOUT_S, lambda: process.kill())
        kill_timer.start()
    except Exception as e:
        logger.exception("Failed to start OpenSCAD process")
        yield json.dumps({
            'event': 'error',
            'part': part,
            'message': f'Internal Process Error: {str(e)}'
        })
        return

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
        _process_manager.clear()

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
            'message': f'Render failed with code {process.returncode}'
        })
        return False


def cancel_render():
    """Kill the active OpenSCAD render process if one is running."""
    return _process_manager.cancel()
