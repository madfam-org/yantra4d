"""
Graph Engine — transpiles node-graph documents (.graph.json) into sandboxed
CadQuery scripts.

The graph engine is yantra4d's fourth engine. Unlike openscad/cadquery/implicit
it owns no kernel process: a graph document is compiled to a CadQuery script
(literals-only substitution, deterministic emission order) and executed through
the existing cq_runner sandbox, so it inherits the render queue, caching, tier
gating, format conversion, and cancellation wholesale.

Format governance: the document contract is `packages/schemas/graph.schema.json`
(version 1.x). This module is the enforcing validator — schema-less documents,
unknown keys, unknown node types, and cycles are all hard errors.

Known cache limit: the render cache keys on the graph file's content hash plus
request params. A manifest edit that only retargets a parameter `binding`
(without touching the graph or the incoming param values) is not reflected in
that key; `ignore_cache` covers the authoring loop.
"""
import hashlib
import json
import keyword
import logging
import math
import os
import re
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

GRAPH_FILE_SUFFIX = ".graph.json"
GRAPH_VERSION_PATTERN = re.compile(r"^1\.\d+(\.\d+)?$")
MAX_GRAPH_BYTES = 256 * 1024
MAX_NODES = 500
MAX_OUTPUTS = 50

_IDENT_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
_BINDING_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)$")
# CadQuery string selectors are data for cq's selector parser, never code, but
# constrain them to the selector grammar's charset anyway.
_SELECTOR_RE = re.compile(r"^[\w|<>%#()+.\- ]*$")

# Identifiers the generated script defines or cq_runner injects; parameter
# bindings may not shadow them.
_RESERVED_IDENTIFIERS = frozenset({
    "cq", "math", "result", "assembly", "part", "show_object", "target_part",
})

_ALLOWED_TOP_KEYS = frozenset({"version", "units", "nodes", "outputs", "meta"})
_ALLOWED_NODE_KEYS = frozenset({"id", "type", "params", "inputs", "meta"})

_AXIS_TUPLES = {"x": "(1, 0, 0)", "y": "(0, 1, 0)", "z": "(0, 0, 1)"}


class GraphError(ValueError):
    """Raised when a graph document fails validation or transpilation."""


# ── Node vocabulary v1 ─────────────────────────────────────────────────────────
# Each type declares typed params (kind, default) and ordered input sockets.
# Emitters receive already-safe expression strings — a param expression is
# always either a validated literal or a `_param(...)` probe, never raw text.

def _emit_box(v, i, p):
    return f"{v} = cq.Workplane(\"XY\").box({p['w']}, {p['d']}, {p['h']})"


def _emit_cylinder(v, i, p):
    return f"{v} = cq.Workplane(\"XY\").cylinder({p['h']}, {p['r']})"


def _emit_sphere(v, i, p):
    return f"{v} = cq.Workplane(\"XY\").sphere({p['r']})"


def _emit_union(v, i, p):
    return f"{v} = {i['a']}.union({i['b']})"


def _emit_cut(v, i, p):
    return f"{v} = {i['a']}.cut({i['b']})"


def _emit_intersect(v, i, p):
    return f"{v} = {i['a']}.intersect({i['b']})"


def _emit_translate(v, i, p):
    return f"{v} = {i['shape']}.translate(({p['x']}, {p['y']}, {p['z']}))"


def _emit_rotate(v, i, p):
    return f"{v} = {i['shape']}.rotate((0, 0, 0), {p['axis']}, {p['angle']})"


def _emit_fillet(v, i, p):
    return f"{v} = {i['shape']}.edges({p['edges']}).fillet({p['radius']})"


def _emit_chamfer(v, i, p):
    return f"{v} = {i['shape']}.edges({p['edges']}).chamfer({p['distance']})"


# kinds: "float" (finite number), "selector" (cq edge selector string, "" = all
# edges), "axis" (x|y|z, emitted as a unit-vector tuple literal).
NODE_TYPES = {
    "box": {
        "params": {"w": ("float", 10.0), "d": ("float", 10.0), "h": ("float", 10.0)},
        "inputs": (),
        "emit": _emit_box,
    },
    "cylinder": {
        "params": {"r": ("float", 5.0), "h": ("float", 10.0)},
        "inputs": (),
        "emit": _emit_cylinder,
    },
    "sphere": {
        "params": {"r": ("float", 5.0)},
        "inputs": (),
        "emit": _emit_sphere,
    },
    "union": {"params": {}, "inputs": ("a", "b"), "emit": _emit_union},
    "cut": {"params": {}, "inputs": ("a", "b"), "emit": _emit_cut},
    "intersect": {"params": {}, "inputs": ("a", "b"), "emit": _emit_intersect},
    "translate": {
        "params": {"x": ("float", 0.0), "y": ("float", 0.0), "z": ("float", 0.0)},
        "inputs": ("shape",),
        "emit": _emit_translate,
    },
    "rotate": {
        "params": {"axis": ("axis", "z"), "angle": ("float", 0.0)},
        "inputs": ("shape",),
        "emit": _emit_rotate,
    },
    "fillet": {
        "params": {"edges": ("selector", ""), "radius": ("float", 1.0)},
        "inputs": ("shape",),
        "emit": _emit_fillet,
    },
    "chamfer": {
        "params": {"edges": ("selector", ""), "distance": ("float", 1.0)},
        "inputs": ("shape",),
        "emit": _emit_chamfer,
    },
}


# ── Literal emission (the security boundary) ──────────────────────────────────

def _float_literal(value, where: str) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise GraphError(f"{where}: expected a number, got {type(value).__name__}")
    value = float(value)
    if not math.isfinite(value):
        raise GraphError(f"{where}: number must be finite")
    return repr(value)


def _selector_literal(value, where: str) -> str:
    if not isinstance(value, str):
        raise GraphError(f"{where}: expected a string selector")
    if len(value) > 120 or not _SELECTOR_RE.match(value):
        raise GraphError(f"{where}: invalid edge selector {value!r}")
    # "" means all edges → emit a no-argument .edges() call.
    return json.dumps(value) if value else ""


def _axis_literal(value, where: str) -> str:
    if value not in _AXIS_TUPLES:
        raise GraphError(f"{where}: axis must be one of x, y, z")
    return _AXIS_TUPLES[value]


def _literal(kind: str, value, where: str) -> str:
    if kind == "float":
        return _float_literal(value, where)
    if kind == "selector":
        return _selector_literal(value, where)
    if kind == "axis":
        return _axis_literal(value, where)
    raise GraphError(f"{where}: unknown param kind {kind!r}")  # pragma: no cover


def _bound_expr(kind: str, pid: str, default_literal: str, where: str) -> str:
    """Expression reading a manifest-bound parameter at render time."""
    if kind == "float":
        return f"float(_param(lambda: {pid}, {default_literal}))"
    if kind == "selector":
        raise GraphError(f"{where}: selector params cannot be bound to manifest parameters")
    if kind == "axis":
        raise GraphError(f"{where}: axis params cannot be bound to manifest parameters")
    raise GraphError(f"{where}: unknown param kind {kind!r}")  # pragma: no cover


# ── Validation ────────────────────────────────────────────────────────────────

def extract_bindings(manifest_parameters: list) -> dict:
    """Map (node_id, param_name) → manifest param id from `binding` entries.

    A parameter's `binding` is either one 'nodeId.param' target or a list of
    them — one manifest parameter may drive several node params (e.g. a hole
    diameter bound to every hole cylinder), but each node param has at most
    one driving parameter.
    """
    bindings: dict[tuple[str, str], str] = {}
    for entry in manifest_parameters or []:
        binding = entry.get("binding")
        if not binding:
            continue
        pid = entry.get("id", "")
        if not _IDENT_RE.match(pid) or keyword.iskeyword(pid):
            raise GraphError(f"parameter '{pid}': id is not bindable (must be a plain identifier)")
        if pid.startswith("_") or pid in _RESERVED_IDENTIFIERS:
            raise GraphError(f"parameter '{pid}': id collides with a reserved name")
        targets = binding if isinstance(binding, list) else [binding]
        for target in targets:
            m = _BINDING_RE.match(target) if isinstance(target, str) else None
            if not m:
                raise GraphError(f"parameter '{pid}': invalid binding {target!r} (want 'nodeId.param')")
            key = (m.group(1), m.group(2))
            if key in bindings:
                raise GraphError(f"binding target {target!r} is bound by more than one parameter")
            bindings[key] = pid
    return bindings


def _validate_document(doc, where: str) -> None:
    if not isinstance(doc, dict):
        raise GraphError(f"{where}: document must be a JSON object")
    unknown = set(doc) - _ALLOWED_TOP_KEYS
    if unknown:
        raise GraphError(f"{where}: unknown top-level keys: {sorted(unknown)}")

    version = doc.get("version")
    if not isinstance(version, str) or not GRAPH_VERSION_PATTERN.match(version):
        raise GraphError(f"{where}: 'version' must match 1.x (got {version!r})")

    units = doc.get("units", "mm")
    if units != "mm":
        raise GraphError(f"{where}: only 'mm' units are supported in graph v1 (got {units!r})")

    nodes = doc.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        raise GraphError(f"{where}: 'nodes' must be a non-empty array")
    if len(nodes) > MAX_NODES:
        raise GraphError(f"{where}: too many nodes ({len(nodes)} > {MAX_NODES})")

    outputs = doc.get("outputs")
    if not isinstance(outputs, dict) or not outputs:
        raise GraphError(f"{where}: 'outputs' must map at least one part id to a node id")
    if len(outputs) > MAX_OUTPUTS:
        raise GraphError(f"{where}: too many outputs ({len(outputs)} > {MAX_OUTPUTS})")


def _validate_nodes(nodes: list, where: str) -> dict:
    """Validate node entries; return {node_id: node} preserving file order."""
    by_id: dict[str, dict] = {}
    for idx, node in enumerate(nodes):
        loc = f"{where}: nodes[{idx}]"
        if not isinstance(node, dict):
            raise GraphError(f"{loc}: must be an object")
        unknown = set(node) - _ALLOWED_NODE_KEYS
        if unknown:
            raise GraphError(f"{loc}: unknown keys: {sorted(unknown)}")

        node_id = node.get("id")
        if not isinstance(node_id, str) or not _IDENT_RE.match(node_id) or keyword.iskeyword(node_id):
            raise GraphError(f"{loc}: 'id' must be a plain identifier (got {node_id!r})")
        if node_id in by_id:
            raise GraphError(f"{loc}: duplicate node id '{node_id}'")

        node_type = node.get("type")
        spec = NODE_TYPES.get(node_type)
        if spec is None:
            raise GraphError(f"{loc}: unknown node type {node_type!r}")

        params = node.get("params", {})
        if not isinstance(params, dict):
            raise GraphError(f"{loc}: 'params' must be an object")
        unknown_params = set(params) - set(spec["params"])
        if unknown_params:
            raise GraphError(f"{loc}: unknown params for '{node_type}': {sorted(unknown_params)}")

        inputs = node.get("inputs", {})
        if not isinstance(inputs, dict):
            raise GraphError(f"{loc}: 'inputs' must be an object")
        expected = set(spec["inputs"])
        if set(inputs) != expected:
            raise GraphError(
                f"{loc}: '{node_type}' requires inputs {sorted(expected)}, got {sorted(inputs)}"
            )
        for socket, ref in inputs.items():
            if not isinstance(ref, str):
                raise GraphError(f"{loc}: input '{socket}' must reference a node id")
            if ref == node_id:
                raise GraphError(f"{loc}: input '{socket}' references the node itself")

        by_id[node_id] = node

    # Dangling references (checked after all ids are known).
    for node_id, node in by_id.items():
        for socket, ref in node.get("inputs", {}).items():
            if ref not in by_id:
                raise GraphError(
                    f"{where}: node '{node_id}' input '{socket}' references unknown node '{ref}'"
                )
    return by_id


def _validate_bindings(bindings: dict, by_id: dict, where: str) -> None:
    for (node_id, param_name), pid in bindings.items():
        node = by_id.get(node_id)
        if node is None:
            raise GraphError(f"{where}: parameter '{pid}' binds unknown node '{node_id}'")
        spec = NODE_TYPES[node["type"]]
        if param_name not in spec["params"]:
            raise GraphError(
                f"{where}: parameter '{pid}' binds '{node_id}.{param_name}' "
                f"but node type '{node['type']}' has no param '{param_name}'"
            )


# ── Transpilation ─────────────────────────────────────────────────────────────

def transpile(doc: dict, bindings: dict | None = None, source_name: str = "graph") -> str:
    """Compile a validated graph document into CadQuery script text.

    Deterministic: emission follows file order (topologically constrained), and
    every substituted value is a validated literal or a `_param` probe reading a
    manifest-bound parameter injected by cq_runner.
    """
    bindings = bindings or {}
    _validate_document(doc, source_name)
    by_id = _validate_nodes(doc["nodes"], source_name)
    _validate_bindings(bindings, by_id, source_name)

    outputs = doc["outputs"]
    for part_id, ref in outputs.items():
        if not isinstance(part_id, str) or not part_id:
            raise GraphError(f"{source_name}: output part ids must be non-empty strings")
        if ref not in by_id:
            raise GraphError(f"{source_name}: output '{part_id}' references unknown node '{ref}'")

    lines = [
        "# Generated by the Yantra4D graph engine - DO NOT EDIT.",
        f"# Source: {source_name}",
        "import cadquery as cq",
        "",
        "",
        "def _param(getter, default):",
        "    try:",
        "        return getter()",
        "    except Exception:  # noqa: BLE001 - sandbox probe for injected params",
        "        return default",
        "",
        "",
    ]

    def _param_expr(node: dict, name: str, kind: str, default) -> str:
        where = f"{source_name}: node '{node['id']}' param '{name}'"
        raw = node.get("params", {}).get(name, default)
        default_literal = _literal(kind, raw, where)
        pid = bindings.get((node["id"], name))
        if pid is None:
            return default_literal
        return _bound_expr(kind, pid, default_literal, where)

    emitted: set[str] = set()
    remaining = list(by_id.values())
    while remaining:
        progressed = False
        still: list[dict] = []
        for node in remaining:
            deps = node.get("inputs", {}).values()
            if any(dep not in emitted for dep in deps):
                still.append(node)
                continue
            spec = NODE_TYPES[node["type"]]
            input_vars = {s: f"_n_{ref}" for s, ref in node.get("inputs", {}).items()}
            param_exprs = {
                name: _param_expr(node, name, kind, default)
                for name, (kind, default) in spec["params"].items()
            }
            lines.append(spec["emit"](f"_n_{node['id']}", input_vars, param_exprs))
            emitted.add(node["id"])
            progressed = True
        if not progressed:
            cyclic = sorted(n["id"] for n in still)
            raise GraphError(f"{source_name}: dependency cycle among nodes {cyclic}")
        remaining = still

    default_part = next(iter(outputs))
    lines.append("")
    lines.append("_outputs = {")
    for part_id, ref in outputs.items():
        lines.append(f"    {json.dumps(part_id)}: _n_{ref},")
    lines.append("}")
    lines.append(f"_target = str(_param(lambda: target_part, {json.dumps(default_part)}))")
    lines.append("result = _outputs.get(_target)")
    lines.append("if result is None:")
    lines.append("    raise ValueError(\"Unknown target_part: \" + _target)")
    lines.append("")
    return "\n".join(lines)


# ── Render-path entrypoint ────────────────────────────────────────────────────

def load_graph_document(graph_path: str) -> tuple[dict, bytes]:
    """Read and parse a .graph.json file with size and suffix guards."""
    if not str(graph_path).endswith(GRAPH_FILE_SUFFIX):
        raise GraphError(f"graph file must end with {GRAPH_FILE_SUFFIX}: {graph_path}")
    path = Path(graph_path)
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise GraphError(f"cannot read graph file {graph_path}: {exc}") from exc
    if len(raw) > MAX_GRAPH_BYTES:
        raise GraphError(f"graph file exceeds {MAX_GRAPH_BYTES} bytes: {graph_path}")
    try:
        doc = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise GraphError(f"graph file is not valid JSON: {exc}") from exc
    return doc, raw


def prepare_graph_script(graph_path: str, manifest) -> str:
    """Transpile a graph file into a CadQuery script on disk; return its path.

    The output filename is keyed by the graph content plus the manifest's
    binding map, so repeated renders reuse the same script and any change to
    either input produces a new file (no stale-overwrite races between parts).
    """
    doc, raw = load_graph_document(graph_path)
    bindings = extract_bindings(getattr(manifest, "parameters", None) or [])

    fingerprint = hashlib.sha256(
        raw + json.dumps(sorted(bindings.items()), sort_keys=True).encode()
    ).hexdigest()

    out_dir = Path(tempfile.gettempdir()) / "yantra4d_graphgen"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"graph_{fingerprint[:24]}.py"
    if out_path.is_file():
        return str(out_path)

    script = transpile(doc, bindings, source_name=os.path.basename(graph_path))

    tmp_path = out_path.with_suffix(".tmp")
    tmp_path.write_text(script)
    os.replace(tmp_path, out_path)
    logger.info("Transpiled graph %s -> %s", graph_path, out_path)
    return str(out_path)
