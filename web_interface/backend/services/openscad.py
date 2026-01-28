"""
OpenSCAD Service
Handles all OpenSCAD subprocess interactions.
"""
import logging
import subprocess
import json
import os

from config import Config

logger = logging.getLogger(__name__)

# Phase weights for progress estimation
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


def build_openscad_command(output_path: str, scad_path: str, params: dict, mode_id: int = 0) -> list:
    """Build OpenSCAD command with parameters."""
    cmd = [Config.OPENSCAD_PATH, "-o", output_path]
    
    for key, value in params.items():
        if key == 'scad_file':
            continue
        if isinstance(value, bool):
            val_str = str(value).lower()
        else:
            val_str = str(value)
        cmd.extend(["-D", f"{key}={val_str}"])
    
    if mode_id != 0:
        cmd.extend(["-D", f"render_mode={mode_id}"])
    
    cmd.append(scad_path)
    return cmd


def run_render(cmd: list) -> tuple[bool, str]:
    """Execute OpenSCAD render synchronously. Returns (success, stderr)."""
    logger.info(f"Running OpenSCAD: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return True, result.stderr
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
    process = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    
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
