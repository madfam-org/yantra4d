"""
SCAD Analyzer — regex-based extraction of variables, modules, includes, and render_mode patterns
from OpenSCAD source files.
"""
import re
from pathlib import Path


def analyze_file(filepath: Path) -> dict:
    """Analyze a single .scad file and return structured data."""
    text = filepath.read_text(encoding="utf-8", errors="replace")
    return {
        "filename": filepath.name,
        "variables": _extract_variables(text),
        "modules": _extract_modules(text),
        "includes": _extract_includes(text),
        "uses": _extract_uses(text),
        "render_modes": _extract_render_modes(text),
        "module_calls": _extract_module_calls(text),
        "attachments": _extract_attachments(text),
    }


def analyze_directory(directory: Path) -> dict:
    """Analyze all .scad files in a directory and return cross-file analysis."""
    files = {}
    for scad_file in sorted(directory.glob("*.scad")):
        files[scad_file.name] = analyze_file(scad_file)

    return {
        "files": files,
        "dependency_graph": _build_dependency_graph(files),
        "entry_points": _identify_entry_points(files),
    }


# --- Variable extraction ---

_VAR_PATTERN = re.compile(
    r"^(\w+)\s*=\s*(.+?)\s*;(?:\s*//\s*(.+))?$",
    re.MULTILINE,
)


def _extract_variables(text: str) -> list[dict]:
    """Extract top-level variable assignments."""
    variables = []
    for match in _VAR_PATTERN.finditer(text):
        name = match.group(1)
        raw_value = match.group(2).strip()
        comment = (match.group(3) or "").strip()

        # Skip module/function definitions that happen to match
        if name in ("module", "function"):
            continue

        var_type, value = _infer_type(raw_value)
        variables.append({
            "name": name,
            "raw_value": raw_value,
            "type": var_type,
            "value": value,
            "comment": comment,
        })
    return variables


def _infer_type(raw: str) -> tuple[str, object]:
    """Infer variable type from its raw string value."""
    if raw in ("true", "false"):
        return "bool", raw == "true"
    if raw.startswith('"') and raw.endswith('"'):
        return "string", raw.strip('"')
    try:
        if "." in raw:
            return "number", float(raw)
        return "number", int(raw)
    except ValueError:
        pass
    # Expression — can't resolve statically
    return "expression", raw


# --- Module extraction ---

_MODULE_PATTERN = re.compile(
    r"^module\s+(\w+)\s*\(([^)]*)\)\s*\{",
    re.MULTILINE,
)

_MODULE_PARAM = re.compile(r"(\w+)(?:\s*=\s*([^,)]+))?")


def _extract_modules(text: str) -> list[dict]:
    """Extract module definitions with their parameters."""
    modules = []
    for match in _MODULE_PATTERN.finditer(text):
        name = match.group(1)
        params_str = match.group(2).strip()
        params = []
        if params_str:
            for pm in _MODULE_PARAM.finditer(params_str):
                params.append({
                    "name": pm.group(1),
                    "default": pm.group(2).strip() if pm.group(2) else None,
                })
        modules.append({"name": name, "parameters": params})
    return modules


# --- Include / Use extraction ---

_INCLUDE_PATTERN = re.compile(r"^include\s*<(.+?)>", re.MULTILINE)
_USE_PATTERN = re.compile(r"^use\s*<(.+?)>", re.MULTILINE)


def _extract_includes(text: str) -> list[str]:
    return _INCLUDE_PATTERN.findall(text)


def _extract_uses(text: str) -> list[str]:
    return _USE_PATTERN.findall(text)


# --- render_mode extraction ---

_RENDER_MODE_PATTERN = re.compile(
    r"render_mode\s*==\s*(\d+)",
)


def _extract_render_modes(text: str) -> list[int]:
    """Detect render_mode == N patterns and return sorted unique values."""
    modes = set()
    for match in _RENDER_MODE_PATTERN.finditer(text):
        modes.add(int(match.group(1)))
    return sorted(modes)


# --- Module call extraction ---

_CALL_PATTERN = re.compile(r"\b(\w+)\s*\(", re.MULTILINE)

# Built-in OpenSCAD modules/functions to exclude
_BUILTINS = {
    "cube", "sphere", "cylinder", "polyhedron", "circle", "square", "polygon",
    "translate", "rotate", "scale", "mirror", "multmatrix", "color",
    "union", "difference", "intersection", "hull", "minkowski",
    "linear_extrude", "rotate_extrude", "surface", "import", "projection",
    "for", "if", "let", "assert", "echo", "render", "children",
    "text", "offset", "resize",
    "cos", "sin", "tan", "acos", "asin", "atan", "atan2",
    "abs", "ceil", "floor", "round", "min", "max", "pow", "sqrt", "exp", "log", "ln",
    "len", "str", "chr", "ord", "concat", "lookup", "search",
    "is_undef", "is_list", "is_num", "is_bool", "is_string",
}


def _extract_module_calls(text: str) -> list[str]:
    """Extract non-builtin module/function calls."""
    calls = set()
    for match in _CALL_PATTERN.finditer(text):
        name = match.group(1)
        if name not in _BUILTINS and not name.startswith("$"):
            calls.add(name)
    return sorted(calls)


# --- Cross-file analysis ---

def _build_dependency_graph(files: dict) -> dict:
    """Build {filename: [dependency_filenames]} from includes/uses."""
    graph = {}
    for fname, analysis in files.items():
        deps = list(set(analysis["includes"] + analysis["uses"]))
        graph[fname] = deps
    return graph


def _identify_entry_points(files: dict) -> list[str]:
    """Identify files that use render_mode (likely entry points) or are not included by others."""
    # Files with render_mode usage are entry points
    entry = [f for f, a in files.items() if a["render_modes"]]

    # Also files not included/used by any other file
    all_deps = set()
    for a in files.values():
        all_deps.update(a["includes"])
        all_deps.update(a["uses"])

    for fname in files:
        if fname not in all_deps and fname not in entry:
            entry.append(fname)

    return sorted(set(entry))


# --- BOSL2 attachment extraction ---

# Matches: attach(ANCHOR) { child_module(...) }
# or:      attach(ANCHOR, PARENT_ANCHOR) { ... }
_ATTACH_PATTERN = re.compile(
    r"\battach\s*\(\s*([\w+]+)(?:\s*,\s*([\w+]+))?\s*\)\s*\{?\s*(\w+)",
    re.MULTILINE,
)

# Matches: position(ANCHOR) { child_module(...) }
_POSITION_PATTERN = re.compile(
    r"\bposition\s*\(\s*([\w+]+)\s*\)\s*\{?\s*(\w+)",
    re.MULTILINE,
)


def _extract_attachments(text: str) -> list[dict]:
    """
    Extract BOSL2 attach() and position() calls.

    Returns a list of dicts:
      {
        "type":          "attach" | "position",
        "anchor":        str,   # anchor on the parent (e.g. "TOP")
        "parent_anchor": str,   # anchor on the child (only for attach())
        "child":         str,   # name of the child module being attached
      }
    """
    results = []

    for m in _ATTACH_PATTERN.finditer(text):
        results.append({
            "type": "attach",
            "anchor": m.group(1),
            "parent_anchor": m.group(2) or m.group(1),
            "child": m.group(3),
        })

    for m in _POSITION_PATTERN.finditer(text):
        results.append({
            "type": "position",
            "anchor": m.group(1),
            "parent_anchor": m.group(1),
            "child": m.group(2),
        })

    return results
