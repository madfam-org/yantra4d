import json
import logging
import math
import os
import sys

from commons_sandbox import read_script, validate_script_path

# cq_runner is launched as a standalone script (its own directory is sys.path[0]),
# so the sibling allowlist module imports flat; it is also importable as part of
# the application package under services.engine for the test suite.
try:  # pragma: no cover - exercised by both invocation styles
    from cq_sandbox import build_cq_sandbox_builtins
    from tessellation import PRINT, profile
except ImportError:  # pragma: no cover
    from services.engine.cq_sandbox import build_cq_sandbox_builtins
    from services.engine.tessellation import PRINT, profile

logger = logging.getLogger(__name__)


def _export_stl_with_profile(cq, result, output_path, tess):
    """Write *result* as binary STL tessellated with the profile *tess*.

    Only non-``print`` profiles come here: the print branch keeps calling the exporter
    exactly as it did before profiles existed. ``cq.exporters.export`` cannot ask for an
    ABSOLUTE linear bound (it calls ``exportStl`` with ``relative`` left at True), so
    the shape's own ``exportStl`` is called, after the same flattening ``export`` does
    internally: a Workplane becomes ``compound(*result)``, an Assembly its
    ``toCompound()``.

    The shape is copied WITHOUT its triangulation first. OCCT stores a face's mesh on
    the face, and ``BRepMesh_IncrementalMesh`` keeps an existing mesh it judges fine
    enough. A shape shared across renders in a warm worker (a sibling cartridge's
    module-level solid, say) would otherwise carry one profile's mesh into another
    profile's export, in either direction. Meshing a fresh copy leaves the original
    untouched and makes the preview mesh depend on the profile alone.
    """
    from cadquery.occ_impl.shapes import compound

    if isinstance(result, cq.Assembly):
        shape = result.toCompound()
    elif isinstance(result, cq.Shape):
        shape = result
    else:
        shape = compound(*result)
    shape.copy(mesh=False).exportStl(
        output_path, tess.linear, tess.angular, ascii=False, relative=tess.relative
    )


def run_cadquery_script(script_path, output_path, params_json, export_format, tessellation=PRINT):
    try:
        import cadquery as cq
    except ImportError as exc:
        # The bare message hid a week of CI archaeology: an import can fail for
        # reasons other than absence (missing libGL on a slim runner image, a
        # failed dlopen under a pod memory limit). Always surface the cause.
        print(f"Error: CadQuery is not installed. ({exc})")
        sys.exit(1)

    # The tessellation profile (services/engine/tessellation.py). The API decides who
    # may ask for which; the runner only refuses what it cannot honour, so a bad value
    # fails the render instead of silently producing a print mesh.
    try:
        tess = profile(tessellation)
    except ValueError as exc:
        print(f"Error: {exc}")
        sys.exit(1)
    if tess.name != PRINT and export_format.upper() != "STL":
        print(f"Error: the {tess.name!r} tessellation profile is only offered for STL exports, "
              f"not {export_format!r}.")
        sys.exit(1)

    print(f"Loading parameters: {params_json}")
    params = json.loads(params_json)

    # The restricted-execution security core is the shared commons-sandbox package
    # (one authored source with Fashion Cabinet's fc_runner). validate_script_path
    # is realpath-checked; CadQuery cartridges may be .py or .cq.
    try:
        validate_script_path(script_path, {".py", ".cq"})
    except ValueError as exc:
        print(f"Error: {exc}")
        sys.exit(1)

    print(f"Executing CadQuery script: {script_path}")
    script_content = read_script(script_path)

    # Allowlist import policy (defence in depth over the shared core's denylist):
    # a cartridge may import only known-safe packages and sibling cartridges on
    # the curated roots. The engine hands those roots down in the environment.
    curated_env = os.environ.get("YANTRA4D_CURATED_ROOTS", "")
    curated_roots = frozenset(p for p in curated_env.split(os.pathsep) if p)
    safe_builtins = build_cq_sandbox_builtins("CadQuery scripts", curated_roots)

    exec_globals = {
        "__builtins__": safe_builtins,
        "cq": cq,
        "math": math,
        "__file__": script_path,
        "__name__": "__main__",
    }
    exec_globals.update(params)

    is_gltf_or_glb = export_format.upper() in ["GLTF", "GLB"]

    # glTF/GLB is produced by transcoding a STEP intermediate through cascadio.
    # The STEP path is decided BEFORE the script runs, and it is what the script
    # sees as `--out`. Twenty-one commons cartridges (the former satellite repos:
    # din-rail-clip, fasteners, gears, motor-mount, spiral-planter, …) carry an
    # `if __name__ == "__main__":` block that parses that argv and calls
    # `cq.exporters.export(res, args.out)` themselves. Handed a `.glb` path,
    # CadQuery cannot infer an export type and raises "Unknown extensions,
    # specify export type explicitly" inside exec — before this runner's own
    # transcode ever ran. Handed the `.step` path, the same scripts write a
    # perfectly good STEP, and the transcode below picks it up. (Found by the
    # first prerender-commons run, 2026-09-19.)
    temp_step_path = None
    if is_gltf_or_glb:
        import tempfile
        try:
            import cascadio
        except ImportError:
            print("Error: cascadio library is missing. Cannot export high-quality GLB.")
            sys.exit(1)
        with tempfile.NamedTemporaryFile(suffix=".step", delete=False) as tmp:
            temp_step_path = tmp.name
        # Empty on purpose: "the script wrote it" is detected by size below.
        os.remove(temp_step_path)
    script_out = temp_step_path if is_gltf_or_glb else output_path

    try:
        # Mock sys.argv so script's argparse doesn't break
        old_argv = sys.argv
        sys.argv = [script_path, "--params", params_json, "--out", script_out]

        # Execute the script. The script should assign the final shape to an 'assembly', 'result', or 'part' variable.
        exec(script_content, exec_globals)  # noqa: S102 — sandboxed via restricted builtins

        # Find the result
        result = None
        for var_name in ['result', 'assembly', 'part', 'show_object']:
            if var_name in exec_globals and isinstance(exec_globals[var_name], (cq.Workplane, cq.Assembly, cq.Shape)):
                result = exec_globals[var_name]
                break

        if result is None:
            # Try to grab the last CadQuery object created
            for key, val in reversed(list(exec_globals.items())):
                if isinstance(val, (cq.Workplane, cq.Assembly, cq.Shape)):
                    result = val
                    break

        # A script that exported itself has done the geometry's job even when it
        # left no module-level shape behind (its `result` may live inside its
        # `__main__` block or a function).
        script_wrote_step = bool(
            temp_step_path and os.path.exists(temp_step_path) and os.path.getsize(temp_step_path) > 0
        )

        if result is None and not script_wrote_step:
            print("Error: Could not find any CadQuery Workplane, Assembly, or Shape in the script to export.")
            sys.exit(1)

        print(f"Exporting to {export_format}: {output_path}")

        if is_gltf_or_glb:
            try:
                if script_wrote_step:
                    print("Script exported its own STEP; transcoding that.")
                elif isinstance(result, cq.Assembly):
                    result.save(temp_step_path, "STEP")
                else:
                    cq.exporters.export(result, temp_step_path, "STEP")

                print("Transcoding STEP to GLB via cascadio...")
                # cascadio creates a far superior, optimized binary GLB mesh
                cascadio.step_to_glb(temp_step_path, output_path)
            finally:
                if temp_step_path and os.path.exists(temp_step_path):
                    os.remove(temp_step_path)

        elif tess.name != PRINT:
            print(f"Tessellation profile {tess.name!r}: linear {tess.linear} "
                  f"({'relative' if tess.relative else 'mm'}), angular {tess.angular} rad")
            _export_stl_with_profile(cq, result, output_path, tess)

        # The print profile: CadQuery's own export defaults, called exactly as before
        # profiles existed (ruling M1, 2026-11-22: print output must not change).
        elif isinstance(result, cq.Assembly):
            result.save(output_path, export_format.upper())
        else:
            cq.exporters.export(result, output_path, export_format.upper())

        print("Rendering complete.")

    except Exception as e:
        print(f"Error executing CadQuery script: {e}")
        sys.exit(1)
    finally:
        sys.argv = old_argv
        if temp_step_path and os.path.exists(temp_step_path):
            os.remove(temp_step_path)

def serve_forever(stdin=None, stdout=None):
    """Persistent worker mode: import CadQuery once, then serve jobs forever.

    Importing cadquery pulls in OCCT and costs 1-3s. Paying that per render made
    every CadQuery job carry a fixed cold-start tax. In ``--serve`` mode the
    import happens once here, at startup, and each subsequent job reuses the
    warm interpreter.

    Protocol: one JSON object per line on stdin, one JSON object per line on
    stdout. Request keys mirror the argv contract exactly — script_path,
    output_path, params_json, export_format, and ``tessellation`` only for a
    profile other than print. Response is
    ``{"ok": bool, "output": str}``; ``output`` carries the same text the
    subprocess mode would have written to stdout, so the caller's error surface
    is unchanged.

    Every job routes through ``run_cadquery_script``, so the commons_sandbox
    validation and restricted-builtins execution are the identical code path as
    the one-shot mode — the security core is not duplicated or relaxed here.
    ``run_cadquery_script`` signals failure with ``sys.exit(1)``; that raises
    SystemExit, which we catch per job so one bad cartridge ends that job rather
    than the worker.
    """
    import contextlib
    import io

    stdin = stdin if stdin is not None else sys.stdin
    stdout = stdout if stdout is not None else sys.stdout

    # Warm the kernel before announcing readiness so the first real job does not
    # pay the import. A failure here is fatal and must be visible: the pool
    # reads this line to decide whether to fall back to per-render spawns.
    try:
        import cadquery  # noqa: F401
        ready = {"ready": True}
    except Exception as exc:
        ready = {"ready": False, "error": f"CadQuery import failed: {exc}"}
    stdout.write(json.dumps(ready) + "\n")
    stdout.flush()
    if not ready["ready"]:
        return

    for line in stdin:
        line = line.strip()
        if not line:
            continue
        buf = io.StringIO()
        try:
            request = json.loads(line)
        except json.JSONDecodeError as exc:
            stdout.write(json.dumps({"ok": False, "output": f"Malformed job: {exc}"}) + "\n")
            stdout.flush()
            continue

        if request.get("cmd") == "shutdown":
            return

        ok = True
        try:
            # Capture the runner's prints so they can be returned to the caller
            # verbatim, matching what capture_output would have collected.
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                run_cadquery_script(
                    request["script_path"],
                    request["output_path"],
                    request["params_json"],
                    request["export_format"],
                    # Absent for print: the pool sends the key only for another
                    # profile, so a print job's request is what it always was.
                    request.get("tessellation", PRINT),
                )
        except SystemExit as exc:
            ok = (exc.code or 0) == 0
        except Exception as exc:
            ok = False
            buf.write(f"Error executing CadQuery script: {exc}\n")

        stdout.write(json.dumps({"ok": ok, "output": buf.getvalue()}) + "\n")
        stdout.flush()


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "--serve":
        serve_forever()
        sys.exit(0)

    if len(sys.argv) < 5:
        print("Usage: python cq_runner.py <script_path> <output_path> <params_json> <export_format> [tessellation]")
        print("       python cq_runner.py --serve")
        sys.exit(1)

    script_path = sys.argv[1]
    output_path = sys.argv[2]
    params_json = sys.argv[3]
    export_format = sys.argv[4]
    # Optional fifth argument: the tessellation profile. build_cadquery_command adds it
    # only for a profile other than print, so a print command is what it always was.
    tessellation = sys.argv[5] if len(sys.argv) >= 6 else PRINT

    run_cadquery_script(script_path, output_path, params_json, export_format, tessellation)
