"""
CadQuery Service
Handles executing Python CadQuery scripts via a subprocess.
"""
import json
import logging
import os
import subprocess
import threading
import time
from collections.abc import Callable

from services.engine.cq_pool import cq_pool
from services.engine.render_engine import RENDER_TIMEOUT_S, ProcessManager
from utils.project_resolver import project_roots

logger = logging.getLogger(__name__)

_cq_process_manager = ProcessManager()


def _cadquery_env():
    env = os.environ.copy()
    pythonpath = env.get("PYTHONPATH", "")
    # Every cartridge root, not just the public commons: a CadQuery script in
    # a client-private cartridge imports its siblings the same way a public one
    # does.
    roots = [str(r) for r in project_roots()]
    parts = roots + ([pythonpath] if pythonpath else [])
    env["PYTHONPATH"] = os.pathsep.join(parts)
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


def _job_from_cmd(cmd: list) -> dict | None:
    """Recover the render job from a command built by build_cadquery_command.

    The warm pool speaks jobs, not argv, but every caller (worker, animations,
    git_ops) hands us a cmd list. Rather than change that contract — and every
    call site with it — we destructure the command we ourselves built, and
    return None for anything that is not exactly that shape so an unexpected
    command still runs down the historical subprocess path.
    """
    if len(cmd) != 6 or not str(cmd[1]).endswith("cq_runner.py"):
        return None
    return {
        "script_path": cmd[2],
        "output_path": cmd[3],
        "params_json": cmd[4],
        "export_format": cmd[5],
    }


def _pool_enabled() -> bool:
    return os.getenv("YANTRA4D_CQ_POOL_ENABLED", "1").strip().lower() not in (
        "0", "false", "no",
    )


def _try_warm_pool(
    cmd: list, is_cancelled: Callable[[], bool] | None = None
) -> tuple[bool, str] | None:
    """Attempt the render on a warm worker. None means 'not handled'."""
    if not _pool_enabled():
        return None
    job = _job_from_cmd(cmd)
    if job is None:
        return None
    try:
        return cq_pool.submit(env=_cadquery_env(), is_cancelled=is_cancelled, **job)
    except Exception:
        logger.warning("CadQuery warm pool raised; falling back to subprocess",
                       exc_info=True)
        return None


def run_render(
    cmd: list, scad_path: str | None = None, is_cancelled: Callable[[], bool] | None = None
) -> tuple[bool, str]:
    """Execute CadQuery render synchronously. Returns (success, stderr/stdout).

    Prefers a warm worker from the CadQuery pool, which has already paid the
    OCCT import cost. Falls back to the historical per-render subprocess spawn
    whenever the pool declines the job (disabled, saturated, unable to start,
    or the worker died mid-job). The returned contract is identical either way.

    Cancellation is honoured on both paths. The pool polls *is_cancelled* while
    waiting and kills the worker if it fires — the render worker always supplies
    that callback, so gating the pool on its absence would have left this lever
    unused in production.
    """
    pooled = _try_warm_pool(cmd, is_cancelled)
    if pooled is not None:
        success, output = pooled
        logger.info("CadQuery render served by warm pool (success=%s)", success)
        return success, output

    logger.info(f"Running CadQuery: {' '.join(cmd)}")
    try:
        if is_cancelled is None:
            result = subprocess.run(
                cmd, check=True, capture_output=True, text=True,
                timeout=RENDER_TIMEOUT_S, env=_cadquery_env()
            )
            return True, result.stdout + result.stderr

        process = _cq_process_manager.start(
            subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=_cadquery_env())
        )
        kill_timer = threading.Timer(RENDER_TIMEOUT_S, lambda: process.kill())
        kill_timer.start()
        try:
            while process.poll() is None:
                if is_cancelled():
                    _cq_process_manager.cancel()
                    break
                time.sleep(0.05)

            stdout_text = process.communicate()[0] or ""
        finally:
            kill_timer.cancel()
            _cq_process_manager.clear()

        if is_cancelled():
            return False, "Render cancelled by user request"

        if process.returncode != 0:
            logger.error("CadQuery failed with code %s", process.returncode)
            return False, stdout_text

        return True, stdout_text
    except subprocess.TimeoutExpired:
        logger.error("CadQuery render timed out after %ds", RENDER_TIMEOUT_S)
        return False, f"Render timed out after {RENDER_TIMEOUT_S} seconds"
    except subprocess.CalledProcessError as e:
        logger.error("CadQuery failed: %s%s", e.stdout, e.stderr)
        return False, e.stdout + e.stderr
    except Exception:
        logger.exception("CadQuery render error")
        return False, "CadQuery render error"


def stream_render(
    cmd: list, part: str, part_base: float, part_weight: float,
    index: int, total: int, scad_path: str | None = None,
    is_cancelled: Callable[[], bool] | None = None
):
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
            'message': f'Internal Process Error: {e!s}'
        })
        return

    try:
        import queue
        q = queue.Queue()
        
        def reader(stream):
            for line_val in iter(stream.readline, ''):
                q.put(line_val)
            q.put(None)
            
        t = threading.Thread(target=reader, args=(process.stdout,))
        t.daemon = True
        t.start()

        lines_read = 0
        while True:
            if is_cancelled and is_cancelled():
                _cq_process_manager.cancel()
                yield json.dumps({
                    'event': 'error',
                    'part': part,
                    'message': 'Render cancelled by user request'
                })
                return

            try:
                line = q.get(timeout=1.0)
                if line is None:
                    break
                    
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
            except queue.Empty:
                if is_cancelled and is_cancelled():
                    _cq_process_manager.cancel()
                    yield json.dumps({
                        'event': 'error',
                        'part': part,
                        'message': 'Render cancelled by user request'
                    })
                    return

                yield json.dumps({
                    'event': 'ping',
                    'part': part,
                    'message': 'keep-alive'
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
