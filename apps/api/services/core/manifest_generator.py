"""
Manifest Generator — produces a draft project.json from SCAD analyzer output.
"""
from pathlib import Path

from services.core.scad_analyzer import analyze_directory

#: Render-time constants a generated (OpenSCAD) manifest starts with, in SERVER
#: seconds: estimate = base_time + units * per_unit + parts * per_part, and the
#: Studio multiplies by `wasm_multiplier` only for a render that runs in the
#: browser (apps/studio/src/services/engine/renderService.ts::estimateRenderTime).
#:
#: Fitted 2026-10-18 (geo-stab H1) to one anonymous server render each of five
#: OpenSCAD cartridges on api.yantra4d.com, wall clock from the client, cache
#: bypassed: motor-mount 2.08 s (2 parts), gear-reducer 3.87 s (5),
#: julia-vase 1.20 s (1), spiral-planter 9.63 s (2), portacosas 1.70 s (6).
#: A least-squares fit in log space with per_unit tied to per_part gave 1.7 s +
#: 0.21 s per unit and per part; rounded, these predict 0.26x-1.9x of each
#: measurement (geometric mean 1.01x). The previous scaffold (5 / 2 / 8)
#: predicted 3x-25x. Parts and units barely separate in five samples, and
#: spiral-planter's 9.6 s is mesh size (65k vertices), which no term here sees:
#: a cartridge author should still measure and override.
#:
#: Not refitted, because not measured: `wasm_multiplier` (browser renders) and
#: CadQuery (a guest cannot render it). `warning_threshold_seconds` stays 60 s:
#: with server constants that are no longer 12x high, the warning fires only
#: for a render that is predicted to take a minute.
DEFAULT_ESTIMATE_CONSTANTS = {
    "base_time": 1.5,
    "per_unit": 0.25,
    "per_part": 0.25,
    "fn_factor": 64,
    "wasm_multiplier": 3,
    "warning_threshold_seconds": 60,
}


def generate_manifest(directory: Path, slug: str | None = None) -> dict:
    """Analyze a directory of SCAD files and generate a draft project.json with warnings."""
    analysis = analyze_directory(directory)
    slug = slug or directory.name

    warnings = []
    parameters = []
    parts = []
    modes = []
    seen_params = set()

    # Collect variables across all files
    for fname, file_data in analysis["files"].items():
        for var in file_data["variables"]:
            if var["name"] in seen_params:
                continue
            seen_params.add(var["name"])

            if var["type"] == "number":
                val = var["value"]
                param = {
                    "id": var["name"],
                    "type": "slider",
                    "default": val,
                    "min": round(val * 0.5, 2) if val > 0 else 0,
                    "max": round(val * 2.0, 2) if val > 0 else 10,
                    "step": _infer_step(val),
                    "label": {"en": _humanize(var["name"])},
                }
                if var["comment"]:
                    param["tooltip"] = {"en": var["comment"]}
                parameters.append(param)

            elif var["type"] == "bool":
                param = {
                    "id": var["name"],
                    "type": "checkbox",
                    "default": var["value"],
                    "label": {"en": _humanize(var["name"])},
                }
                if var["comment"]:
                    param["tooltip"] = {"en": var["comment"]}
                parameters.append(param)

            elif var["type"] == "string":
                param = {
                    "id": var["name"],
                    "type": "text",
                    "default": var["value"],
                    "label": {"en": _humanize(var["name"])},
                }
                if var["comment"]:
                    param["tooltip"] = {"en": var["comment"]}
                parameters.append(param)

    # Build modes from entry point files
    entry_points = analysis["entry_points"]
    if not entry_points:
        entry_points = list(analysis["files"].keys())
        warnings.append("No entry point files detected (no render_mode usage). Using all files as modes.")

    render_mode_counter = 0
    for fname in entry_points:
        file_data = analysis["files"].get(fname)
        if not file_data:
            continue

        mode_id = Path(fname).stem
        detected_modes = file_data["render_modes"]

        if detected_modes:
            mode_parts = []
            for rm in detected_modes:
                part_id = f"{mode_id}_part_{rm}"
                parts.append({
                    "id": part_id,
                    "render_mode": rm,
                    "label": {"en": f"Part {rm}"},
                    "default_color": _default_color(render_mode_counter),
                })
                mode_parts.append(part_id)
                render_mode_counter += 1

            modes.append({
                "id": mode_id,
                "scad_file": fname,
                "label": {"en": _humanize(mode_id)},
                "parts": mode_parts,
                "estimate": {"base_units": len(mode_parts), "formula": "constant"},
            })
        else:
            # No render_mode — single part
            part_id = f"{mode_id}_main"
            parts.append({
                "id": part_id,
                "render_mode": 0,
                "label": {"en": _humanize(mode_id)},
                "default_color": _default_color(render_mode_counter),
            })
            render_mode_counter += 1
            modes.append({
                "id": mode_id,
                "scad_file": fname,
                "label": {"en": _humanize(mode_id)},
                "parts": [part_id],
                "estimate": {"base_units": 1, "formula": "constant"},
            })
            warnings.append(f"{fname}: No render_mode convention detected. Single-part mode assumed.")

    # Generate warnings
    if not parameters:
        warnings.append("No parameterizable variables detected.")

    for param in parameters:
        if param["type"] == "slider" and param["min"] == param["max"]:
            warnings.append(f"Parameter '{param['id']}': min equals max — review range.")

    if not any(f.get("render_modes") for f in analysis["files"].values()):
        warnings.append("No render_mode patterns found in any file. Parts cannot be rendered independently.")

    warnings.append("No camera_views defined — add manually for best 3D preview experience.")
    warnings.append("No estimate formula tuned — render time estimates will use defaults.")

    manifest = {
        "project": {
            "name": _humanize(slug),
            "slug": slug,
            "version": "0.1.0",
        },
        "modes": modes,
        "parts": parts,
        "parameters": parameters,
        "camera_views": [
            {"id": "iso", "label": {"en": "Isometric"}, "position": [50, 50, 50]},
            {"id": "front", "label": {"en": "Front"}, "position": [0, -100, 0]},
        ],
        "estimate_constants": dict(DEFAULT_ESTIMATE_CONSTANTS),
    }

    return {
        "manifest": manifest,
        "analysis": analysis,
        "warnings": warnings,
    }


def _infer_step(value: float) -> float:
    """Infer a reasonable step size from a numeric value."""
    if isinstance(value, int) or (isinstance(value, float) and value == int(value)):
        return 1
    # Count decimal places
    s = str(value)
    if "." in s:
        decimals = len(s.split(".")[1])
        return round(10 ** (-decimals), decimals)
    return 1


def _humanize(name: str) -> str:
    """Convert snake_case to Title Case."""
    return name.replace("_", " ").replace("-", " ").title()


_COLORS = [
    "#e5e7eb", "#ffffff", "#000000", "#808080", "#ffd700",
    "#ff8c00", "#4a90d9", "#50c878", "#ff6b6b", "#9b59b6",
]


def _default_color(index: int) -> str:
    return _COLORS[index % len(_COLORS)]
