"""
CadQuery Service
Handles executing Python CadQuery scripts via a subprocess.
"""
import logging
import os
import subprocess
import json
import threading

from config import Config
from services.engine.render_engine import RENDER_TIMEOUT_S, ProcessManager

logger = logging.getLogger(__name__)

_cq_process_manager = ProcessManager()


def _cadquery_env():
    env = os.environ.copy()
    pythonpath = env.get("PYTHONPATH", "")
    projects_dir = str(Config.PROJECTS_DIR)
    env["PYTHONPATH"] = f"{projects_dir}{os.pathsep}{pythonpath}" if pythonpath else projects_dir
    return env


def build_cadquery_command(output_path: str, script_path: str, params: dict, export_format: str) -> list:
    """Build Python command to run the CadQuery wrapper script."""
    runner_script = os.path.join(os.path.dirname(__file__), 'cq_runner.py')

    # Pass parameters as a JSON string to the runner
    params_json = json.dumps(params)

    cmd = [
        "python", runner_script,
        script_path, output_path, params_json, export_format
    ]
    return cmd


def run_render(cmd: list, scad_path: str | None = None) -> tuple[bool, str]:
    """Execute CadQuery render synchronously. Returns (success, stderr/stdout)."""
    logger.info(f"Running CadQuery: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=RENDER_TIMEOUT_S, env=_cadquery_env())
        return True, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        logger.error("CadQuery render timed out after %ds", RENDER_TIMEOUT_S)
        return False, f"Render timed out after {RENDER_TIMEOUT_S} seconds"
    except subprocess.CalledProcessError as e:
        logger.error(f"CadQuery failed: {e.stdout}\n{e.stderr}")
        return False, e.stdout + e.stderr


def stream_render(cmd: list, part: str, part_base: float, part_weight: float, index: int, total: int, scad_path: str | None = None):
    """
    Generator that streams CadQuery progress as SSE events.
    """
    # Simply report start and end with some basic streaming
    yield json.dumps({
        'event': 'part_start',
        'part': part,
        'progress': round(part_base),
        'index': index,
        'total': total
    })

    try:
        process = _cq_process_manager.start(
            subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=_cadquery_env())
        )
        kill_timer = threading.Timer(RENDER_TIMEOUT_S, lambda: process.kill())
        kill_timer.start()
    except Exception as e:
        logger.exception("Failed to start CadQuery process")
        yield json.dumps({
            'event': 'error',
            'part': part,
            'message': f'Internal Process Error: {str(e)}'
        })
        return

    try:
        lines_read = 0
        for line in process.stdout:
            line = line.strip()
            if not line:
                continue

            lines_read += 1
            # Fake progress based on output lines (since we don't have exact phases)
            progress_incr = min(80, lines_read * 5)
            overall_progress = part_base + (progress_incr / 100) * part_weight

            yield json.dumps({
                'event': 'output',
                'part': part,
                'line': line,
                'progress': round(overall_progress)
            })

        process.wait()
    finally:
        kill_timer.cancel()
        _cq_process_manager.clear()

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
    """Kill the active CadQuery render process."""
    return _cq_process_manager.cancel()
