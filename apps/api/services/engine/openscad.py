"""
OpenSCAD Service
Handles all OpenSCAD subprocess interactions.
"""
import json
import logging
import os
import queue
import re
import subprocess
import tempfile
import threading
import time
from collections.abc import Callable
from pathlib import Path

from config import Config
from manifest import get_manifest
from services.engine.render_engine import RENDER_TIMEOUT_S, ProcessManager, RenderResult

logger = logging.getLogger(__name__)


def compute_scad_hash(scad_path: str) -> str | None:
    """Compute MD5 hash of SCAD file content for cache invalidation."""
    try:
        import hashlib
        return hashlib.md5(Path(scad_path).read_bytes()).hexdigest()
    except OSError:
        return None


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
    fonts_dirs = []

    if Config.FONTS_DIR and Config.FONTS_DIR.is_dir():
        fonts_dirs.append(str(Config.FONTS_DIR))

    if scad_path:
        project_dir = str(Path(scad_path).parent)
        paths.insert(0, project_dir)
        
        local_fonts = os.path.join(project_dir, "fonts")
        if os.path.isdir(local_fonts) and local_fonts not in fonts_dirs:
            fonts_dirs.append(local_fonts)
                
    if fonts_dirs:
        cache_key = ":".join(fonts_dirs)
        if cache_key not in _fontconfig_cache:
            fd, conf_path = tempfile.mkstemp(suffix=".conf", prefix="fc_yantra_")
            
            dir_tags = "\n".join([f'  <dir>{d}</dir>' for d in fonts_dirs])
            
            os.write(fd, (
                '<?xml version="1.0"?>\n'
                '<!DOCTYPE fontconfig SYSTEM "fonts.dtd">\n'
                '<fontconfig>\n'
                f'{dir_tags}\n'
                '  <include ignore_missing="yes">/etc/fonts/fonts.conf</include>\n'
                '</fontconfig>\n'
            ).encode())
            os.close(fd)
            _fontconfig_cache[cache_key] = conf_path
            logger.info("Created fontconfig for %s → %s", cache_key, conf_path)
        env["FONTCONFIG_FILE"] = _fontconfig_cache[cache_key]

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
            if not re.match(r'^[a-zA-Z0-9 _.#,-]*$', str_val):
                logger.warning(f"Rejecting unsafe text value for {key}")
                continue
            maxlen = defn.get("maxlength", 255)
            if len(str_val) > maxlen:
                str_val = str_val[:maxlen]
            cleaned[key] = str_val
        elif param_type == "checkbox":
            if isinstance(value, bool):
                cleaned[key] = 1 if value else 0
            elif isinstance(value, (int, float)) and value in (0, 1, 0.0, 1.0):
                cleaned[key] = int(value)
            elif str(value).lower() in ("true", "false"):
                cleaned[key] = 1 if str(value).lower() == "true" else 0
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
    cleaned.pop('render_mode', None)

    return cleaned


# ---------------------------------------------------------------------------
# Geometry backend selection (CGAL vs Manifold)
# ---------------------------------------------------------------------------
# OpenSCAD 2023+ ships a second geometry kernel, Manifold, selected with
# `--backend=`. CGAL degrades superlinearly on the boolean- and thread-heavy
# cartridges that dominate this commons; measured locally on
# projects/faircap-filter (BOSL2 threading) with OpenSCAD 2026.02.13:
# CGAL 47.44s vs Manifold 6.62s, both watertight, volumes agreeing to 5e-7.
#
# Support cannot be assumed: release builds predating the feature reject the
# flag, and some nightlies already default to Manifold. So probe the actual
# installed binary once, and cache it — a subprocess per render would spend the
# win it is meant to deliver.

BACKEND_AUTO = "auto"
BACKEND_CGAL = "cgal"
BACKEND_MANIFOLD = "manifold"

# Canonical spellings OpenSCAD accepts for --backend (it matches case-insensitively
# but we emit its own documented casing).
_BACKEND_ARG = {BACKEND_CGAL: "CGAL", BACKEND_MANIFOLD: "Manifold"}

_backend_probe_lock = threading.Lock()
_backend_probe: dict | None = None


def _probe_openscad_backend() -> dict:
    """Interrogate the installed OpenSCAD binary for --backend support.

    Returns a dict with ``supported`` (bool), ``version`` (str|None) and
    ``detail`` (str, for logging/diagnosis).

    Detection reads ``--help`` for the flag rather than trying a render with it.
    That matters: this binary exits 0 for ``--backend=NotABackend`` and only
    reports the rejection on stderr, so an exit code is not evidence the flag
    was honoured. Presence in the help text is.
    """
    binary = Config.OPENSCAD_PATH
    version = None
    try:
        # check=False: a nonzero exit still carries the banner we want to read,
        # and a failed probe must degrade, never raise into the render path.
        vproc = subprocess.run(
            [binary, "--version"], capture_output=True, text=True, timeout=15,
            check=False,
        )
        # OpenSCAD historically prints its version banner on stderr.
        version = ((vproc.stdout or "") + (vproc.stderr or "")).strip().splitlines()
        version = version[0].strip() if version else None
    except Exception as exc:
        logger.warning("OpenSCAD version probe failed for %s: %s", binary, exc)

    try:
        # check=False: some builds exit nonzero from --help; the text is what matters.
        proc = subprocess.run(
            [binary, "--help"], capture_output=True, text=True, timeout=15,
            check=False,
        )
    except Exception as exc:
        logger.warning(
            "OpenSCAD backend probe failed for %s (%s); assuming no --backend support",
            binary, exc,
        )
        return {"supported": False, "version": version,
                "detail": f"probe failed: {exc}"}

    help_text = (proc.stdout or "") + (proc.stderr or "")
    supported = "--backend" in help_text
    detail = ("--backend advertised in --help" if supported
              else "--backend absent from --help")
    logger.info(
        "OpenSCAD backend probe: %s (version=%s, binary=%s)", detail, version, binary
    )
    return {"supported": supported, "version": version, "detail": detail}


def get_backend_probe() -> dict:
    """Return the cached backend probe, running it once on first use."""
    global _backend_probe
    if _backend_probe is None:
        with _backend_probe_lock:
            if _backend_probe is None:
                _backend_probe = _probe_openscad_backend()
    return _backend_probe


def reset_backend_probe() -> None:
    """Drop the cached probe. For tests and for OPENSCAD_PATH changes."""
    global _backend_probe
    with _backend_probe_lock:
        _backend_probe = None


def effective_backend() -> str | None:
    """Resolve the backend to pass to OpenSCAD, or None to pass no flag.

    ``YANTRA4D_OPENSCAD_BACKEND`` accepts ``auto`` (default), ``manifold`` or
    ``cgal``. ``auto`` uses Manifold when the binary advertises it and otherwise
    behaves exactly as before this change — no flag at all. An explicit choice
    is honoured only if the binary supports the flag; asking for a backend a
    binary cannot select would abort every render, so we warn and fall back.
    """
    requested = os.getenv("YANTRA4D_OPENSCAD_BACKEND", BACKEND_AUTO).strip().lower()
    if requested not in (BACKEND_AUTO, BACKEND_CGAL, BACKEND_MANIFOLD):
        logger.warning(
            "Unknown YANTRA4D_OPENSCAD_BACKEND=%r; falling back to %r",
            requested, BACKEND_AUTO,
        )
        requested = BACKEND_AUTO

    if not get_backend_probe()["supported"]:
        if requested != BACKEND_AUTO:
            logger.warning(
                "YANTRA4D_OPENSCAD_BACKEND=%s requested but this OpenSCAD build "
                "has no --backend flag; rendering with the built-in default",
                requested,
            )
        return None

    if requested == BACKEND_AUTO:
        return _BACKEND_ARG[BACKEND_MANIFOLD]
    return _BACKEND_ARG[requested]


def backend_cache_signature() -> str:
    """Identity of the geometry backend, for the render cache key.

    Manifold and CGAL are different evaluators and can produce different
    tessellations for identical parameters. See render_cache._make_key: this
    string is folded into the key so their outputs can never be served for one
    another.
    """
    probe = get_backend_probe()
    backend = effective_backend() or "default"
    return f"{backend}|{probe.get('version') or 'unknown'}"


def build_openscad_command(output_path: str, scad_path: str, params: dict, mode_id: int = 0) -> list:
    """Build OpenSCAD command with parameters."""
    cmd = [Config.OPENSCAD_PATH, "-o", output_path]

    # Geometry backend. Appended after -o/output so the historical positional
    # contract (cmd[0]=binary, cmd[1]="-o", cmd[2]=output, cmd[-1]=scad) holds.
    backend = effective_backend()
    if backend:
        cmd.append(f"--backend={backend}")

    for key, value in params.items():
        if key == 'scad_file':
            continue
        if isinstance(value, bool):
            val_str = "1" if value else "0"
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


def run_render(
    cmd: list, scad_path: str | None = None, is_cancelled: Callable[[], bool] | None = None
) -> RenderResult:
    """Execute OpenSCAD render synchronously.

    Returns a RenderResult dataclass. Supports tuple unpacking for backward
    compatibility: ``success, stderr = run_render(cmd)``.
    """

    logger.info(f"Running OpenSCAD: {_sanitize_cmd_for_log(cmd)}")
    t0 = time.monotonic()
    output_path = None

    # Extract output_path from cmd: the -o flag value
    for i, arg in enumerate(cmd):
        if arg == "-o" and i + 1 < len(cmd):
            output_path = cmd[i + 1]
            break

    try:
        # Default path: preserve historical behavior for tests and legacy callers.
        if is_cancelled is None:
            result = subprocess.run(
                cmd, check=True, capture_output=True, text=True,
                timeout=RENDER_TIMEOUT_S, env=_openscad_env(scad_path)
            )
            duration_ms = (time.monotonic() - t0) * 1000
            # After successful STL render, also produce 3MF for color-preserving viewer delivery
            if output_path and output_path.endswith('.stl'):
                threemf_path = output_path.rsplit('.stl', 1)[0] + '.3mf'
                threemf_cmd = [threemf_path if arg == output_path else arg for arg in cmd]
                try:
                    subprocess.run(threemf_cmd, check=True, capture_output=True, text=True,
                                   timeout=RENDER_TIMEOUT_S, env=_openscad_env(scad_path))
                    logger.info(f"Color-preserving 3MF also generated: {threemf_path}")
                except Exception:
                    pass  # 3MF is optional — STL viewer fallback still works

            return RenderResult(success=True, stderr=result.stderr, output_path=output_path, duration_ms=duration_ms)

        process = _process_manager.start(
            subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=_openscad_env(scad_path)
            )
        )
        kill_timer = threading.Timer(RENDER_TIMEOUT_S, lambda: process.kill())
        kill_timer.start()
        try:
            while process.poll() is None:
                if is_cancelled():
                    _process_manager.cancel()
                    break
                time.sleep(0.05)

            _, stderr = process.communicate()
        finally:
            duration_ms = (time.monotonic() - t0) * 1000
            kill_timer.cancel()
            _process_manager.clear()

        if is_cancelled():
            return RenderResult(
                success=False,
                stderr="Render cancelled by user request",
                output_path=output_path,
                duration_ms=duration_ms,
            )

        if process.returncode != 0:
            logger.error(f"OpenSCAD failed with code {process.returncode}: {stderr}")
            return RenderResult(success=False, stderr=stderr, output_path=output_path, duration_ms=duration_ms)

        if output_path and output_path.endswith('.stl'):
            threemf_path = output_path.rsplit('.stl', 1)[0] + '.3mf'
            threemf_cmd = [threemf_path if arg == output_path else arg for arg in cmd]
            try:
                subprocess.run(threemf_cmd, check=True, capture_output=True, text=True,
                               timeout=RENDER_TIMEOUT_S, env=_openscad_env(scad_path))
                logger.info(f"Color-preserving 3MF also generated: {threemf_path}")
            except Exception:
                pass  # 3MF is optional — STL viewer fallback still works

        return RenderResult(success=True, stderr=stderr, output_path=output_path, duration_ms=duration_ms)

    except subprocess.TimeoutExpired:
        duration_ms = (time.monotonic() - t0) * 1000
        logger.error("OpenSCAD render timed out after %ds", RENDER_TIMEOUT_S)
        return RenderResult(success=False, stderr=f"Render timed out after {RENDER_TIMEOUT_S} seconds", duration_ms=duration_ms)
    except subprocess.CalledProcessError as e:
        duration_ms = (time.monotonic() - t0) * 1000
        stderr = e.stderr or e.output or str(e)
        logger.exception("OpenSCAD render error")
        return RenderResult(success=False, stderr=stderr, output_path=output_path, duration_ms=duration_ms)
    except Exception as e:
        duration_ms = (time.monotonic() - t0) * 1000
        logger.exception("OpenSCAD render error")
        return RenderResult(success=False, stderr=str(e), output_path=output_path, duration_ms=duration_ms)
def stream_render(cmd: list, part: str, part_base: float, part_weight: float, index: int, total: int, scad_path: str | None = None, is_cancelled: Callable[[], bool] | None = None):
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
            'message': f'Internal Process Error: {e!s}'
        })
        return

    try:
        q = queue.Queue()
        
        def reader(stream):
            for line_val in iter(stream.readline, ''):
                q.put(line_val)
            q.put(None)
            
        t = threading.Thread(target=reader, args=(process.stderr,))
        t.daemon = True
        t.start()

        while True:
            if is_cancelled and is_cancelled():
                _process_manager.cancel()
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
            except queue.Empty:
                if is_cancelled and is_cancelled():
                    _process_manager.cancel()
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
        _process_manager.clear()

    if process.returncode == 0:
        final_progress = part_base + part_weight
        yield json.dumps({
            'event': 'part_done', 
            'part': part, 
            'progress': round(final_progress)
        })
    else:
        yield json.dumps({
            'event': 'error',
            'part': part,
            'message': f'Render failed with code {process.returncode}'
        })


def cancel_render():
    """Kill the active OpenSCAD render process if one is running."""
    return _process_manager.cancel()
