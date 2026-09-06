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

A node param is a literal, a `{"param": id}` reference to a manifest parameter,
or an `{"expr": "..."}` expression over manifest parameters (see
`services/engine/graph_expr.py`). Expressions are parsed and type-checked here,
at transpile time, and emitted as arithmetic over the same `_param` probes a
binding emits — so a derived dimension stays live at render time instead of
freezing into a constant, and the cache key (graph content + binding map) stays
correct. An expression that references nothing live folds to a number.

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

from .graph_expr import (
    EXPR_RUNTIME_LINES,
    GraphExprError,
    compile_expression,
    expression_identifiers,
    is_emittable_identifier,
)

logger = logging.getLogger(__name__)

GRAPH_FILE_SUFFIX = ".graph.json"
GRAPH_VERSION_PATTERN = re.compile(r"^1\.\d+(\.\d+)?$")
MAX_GRAPH_BYTES = 256 * 1024
MAX_NODES = 500
MAX_OUTPUTS = 50
# Pattern repeat ceiling. Each repeat is a boolean union, so an unbounded count
# is a denial-of-service against the render worker, not just a slow render.
MAX_PATTERN_COUNT = 200

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

# A param value that is an object is one of these forms, and exactly one key.
_PARAM_REF_KEY = "param"
_PARAM_EXPR_KEY = "expr"
_ALLOWED_PARAM_OBJECT_KEYS = frozenset({_PARAM_REF_KEY, _PARAM_EXPR_KEY})

# Numeric kinds are the only ones an expression or a `{"param": id}` reference
# may produce. Structural kinds (selector, axis, plane) stay literal so a
# render-time value can never change the *shape* of the emitted code.
_BINDABLE_KINDS = frozenset({"float", "count"})

_AXIS_TUPLES = {"x": "(1, 0, 0)", "y": "(0, 1, 0)", "z": "(0, 0, 1)"}
_PLANES = frozenset({"XY", "XZ", "YZ"})


class GraphError(ValueError):
    """Raised when a graph document fails validation or transpilation."""


# ── Node vocabulary ────────────────────────────────────────────────────────────
# Each type declares typed params (kind, default), typed input sockets
# ({socket: required_output_type}), and its own output type — "solid" or
# "profile" (a 2D sketch that only extrude consumes). Emitters receive
# already-safe expression strings: a param expression is always either a
# validated literal or a `_param(...)` probe, never raw text. An emitter
# returns one line or a list of lines.
#
# Deliberately absent: revolve. A 360° revolve blew the memory budget hard
# enough to kill the process during vocabulary bring-up, and the render worker
# must not host an operation that can hang a job. It returns once it is proven
# bounded.

def _emit_box(v, i, p):
    return f"{v} = cq.Workplane(\"XY\").box({p['w']}, {p['d']}, {p['h']})"


def _emit_cylinder(v, i, p):
    return f"{v} = cq.Workplane(\"XY\").cylinder({p['h']}, {p['r']})"


def _emit_sphere(v, i, p):
    return f"{v} = cq.Workplane(\"XY\").sphere({p['r']})"


def _emit_profile_rect(v, i, p):
    return f"{v} = cq.Workplane({p['plane']}).center({p['x']}, {p['y']}).rect({p['w']}, {p['d']})"


def _emit_profile_circle(v, i, p):
    return f"{v} = cq.Workplane({p['plane']}).center({p['x']}, {p['y']}).circle({p['r']})"


def _emit_profile_polygon(v, i, p):
    return (
        f"{v} = cq.Workplane({p['plane']}).center({p['x']}, {p['y']})"
        f".polygon({p['sides']}, {p['diameter']})"
    )


def _emit_extrude(v, i, p):
    return f"{v} = {i['profile']}.extrude({p['height']})"


def _emit_shell(v, i, p):
    # Negative thickness hollows inward, leaving the selected face open.
    return f"{v} = {i['shape']}.faces({p['face']}).shell(-{p['thickness']})"


def _emit_hole(v, i, p):
    return f"{v} = {i['shape']}.faces(\">Z\").workplane().hole({p['diameter']})"


def _emit_mirror(v, i, p):
    return f"{v} = {i['shape']}.union({i['shape']}.mirror({p['plane']}))"


def _emit_pattern_linear(v, i, p):
    src = i["shape"]
    loop = f"_i{v}"
    offset = f"({p['dx']} * {loop}, {p['dy']} * {loop}, {p['dz']} * {loop})"
    return [
        f"{v} = {src}",
        f"for {loop} in range(1, {p['count']}):",
        f"    {v} = {v}.union({src}.translate({offset}))",
    ]


def _emit_pattern_polar(v, i, p):
    src = i["shape"]
    loop = f"_i{v}"
    spin = f"rotate((0, 0, 0), (0, 0, 1), {p['angle']} * {loop})"
    return [
        f"{v} = {src}",
        f"for {loop} in range(1, {p['count']}):",
        f"    {v} = {v}.union({src}.{spin})",
    ]


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


# Param kinds: "float" (finite number), "count" (int, clamped 1..MAX_PATTERN_COUNT
# at render time so a bound parameter cannot detonate a union loop), "selector"
# (cq edge/face selector string, "" = all edges), "axis" (x|y|z as a unit vector),
# "plane" (XY|XZ|YZ workplane name).
NODE_TYPES = {
    # ── Solids ────────────────────────────────────────────────────────────────
    "box": {
        "params": {"w": ("float", 10.0), "d": ("float", 10.0), "h": ("float", 10.0)},
        "inputs": {},
        "output": "solid",
        "emit": _emit_box,
    },
    "cylinder": {
        "params": {"r": ("float", 5.0), "h": ("float", 10.0)},
        "inputs": {},
        "output": "solid",
        "emit": _emit_cylinder,
    },
    "sphere": {
        "params": {"r": ("float", 5.0)},
        "inputs": {},
        "output": "solid",
        "emit": _emit_sphere,
    },
    # ── 2D profiles (consumed by extrude) ─────────────────────────────────────
    "profile_rect": {
        "params": {
            "w": ("float", 10.0), "d": ("float", 10.0),
            "x": ("float", 0.0), "y": ("float", 0.0), "plane": ("plane", "XY"),
        },
        "inputs": {},
        "output": "profile",
        "emit": _emit_profile_rect,
    },
    "profile_circle": {
        "params": {
            "r": ("float", 5.0),
            "x": ("float", 0.0), "y": ("float", 0.0), "plane": ("plane", "XY"),
        },
        "inputs": {},
        "output": "profile",
        "emit": _emit_profile_circle,
    },
    "profile_polygon": {
        "params": {
            "sides": ("count", 6), "diameter": ("float", 20.0),
            "x": ("float", 0.0), "y": ("float", 0.0), "plane": ("plane", "XY"),
        },
        "inputs": {},
        "output": "profile",
        "emit": _emit_profile_polygon,
    },
    "extrude": {
        "params": {"height": ("float", 10.0)},
        "inputs": {"profile": "profile"},
        "output": "solid",
        "emit": _emit_extrude,
    },
    # ── Booleans ──────────────────────────────────────────────────────────────
    "union": {
        "params": {}, "inputs": {"a": "solid", "b": "solid"},
        "output": "solid", "emit": _emit_union,
    },
    "cut": {
        "params": {}, "inputs": {"a": "solid", "b": "solid"},
        "output": "solid", "emit": _emit_cut,
    },
    "intersect": {
        "params": {}, "inputs": {"a": "solid", "b": "solid"},
        "output": "solid", "emit": _emit_intersect,
    },
    # ── Transforms ────────────────────────────────────────────────────────────
    "translate": {
        "params": {"x": ("float", 0.0), "y": ("float", 0.0), "z": ("float", 0.0)},
        "inputs": {"shape": "solid"},
        "output": "solid",
        "emit": _emit_translate,
    },
    "rotate": {
        "params": {"axis": ("axis", "z"), "angle": ("float", 0.0)},
        "inputs": {"shape": "solid"},
        "output": "solid",
        "emit": _emit_rotate,
    },
    "mirror": {
        "params": {"plane": ("plane", "YZ")},
        "inputs": {"shape": "solid"},
        "output": "solid",
        "emit": _emit_mirror,
    },
    # ── Patterns ──────────────────────────────────────────────────────────────
    "pattern_linear": {
        "params": {
            "count": ("count", 3),
            "dx": ("float", 10.0), "dy": ("float", 0.0), "dz": ("float", 0.0),
        },
        "inputs": {"shape": "solid"},
        "output": "solid",
        "emit": _emit_pattern_linear,
    },
    "pattern_polar": {
        "params": {"count": ("count", 4), "angle": ("float", 90.0)},
        "inputs": {"shape": "solid"},
        "output": "solid",
        "emit": _emit_pattern_polar,
    },
    # ── Finishing ─────────────────────────────────────────────────────────────
    "fillet": {
        "params": {"edges": ("selector", ""), "radius": ("float", 1.0)},
        "inputs": {"shape": "solid"},
        "output": "solid",
        "emit": _emit_fillet,
    },
    "chamfer": {
        "params": {"edges": ("selector", ""), "distance": ("float", 1.0)},
        "inputs": {"shape": "solid"},
        "output": "solid",
        "emit": _emit_chamfer,
    },
    "shell": {
        "params": {"thickness": ("float", 2.0), "face": ("selector", ">Z")},
        "inputs": {"shape": "solid"},
        "output": "solid",
        "emit": _emit_shell,
    },
    "hole": {
        "params": {"diameter": ("float", 5.0)},
        "inputs": {"shape": "solid"},
        "output": "solid",
        "emit": _emit_hole,
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


def _plane_literal(value, where: str) -> str:
    if value not in _PLANES:
        raise GraphError(f"{where}: plane must be one of {sorted(_PLANES)}")
    return json.dumps(value)


def _count_literal(value, where: str) -> str:
    if isinstance(value, bool) or not isinstance(value, int):
        raise GraphError(f"{where}: expected a whole number, got {type(value).__name__}")
    if not 1 <= value <= MAX_PATTERN_COUNT:
        raise GraphError(f"{where}: count must be between 1 and {MAX_PATTERN_COUNT}")
    return repr(value)


def _literal(kind: str, value, where: str) -> str:
    if kind == "float":
        return _float_literal(value, where)
    if kind == "count":
        return _count_literal(value, where)
    if kind == "selector":
        return _selector_literal(value, where)
    if kind == "axis":
        return _axis_literal(value, where)
    if kind == "plane":
        return _plane_literal(value, where)
    raise GraphError(f"{where}: unknown param kind {kind!r}")  # pragma: no cover


def _bound_expr(kind: str, pid: str, default_literal: str, where: str) -> str:
    """Expression reading a manifest-bound parameter at render time.

    Only numeric kinds are bindable. Structural params (selector, axis, plane)
    stay literal so the emitted code's shape cannot change at render time.
    Counts are clamped in the generated code: a slider wired to a pattern count
    must never be able to detonate a union loop inside the render worker.
    """
    if kind == "float":
        return f"float(_param(lambda: {pid}, {default_literal}))"
    if kind == "count":
        return (
            f"min(max(int(_param(lambda: {pid}, {default_literal})), 1), {MAX_PATTERN_COUNT})"
        )
    if kind in ("selector", "axis", "plane"):
        raise GraphError(f"{where}: {kind} params cannot be bound to manifest parameters")
    raise GraphError(f"{where}: unknown param kind {kind!r}")  # pragma: no cover


def _numeric_wrapper(kind: str, code: str, where: str) -> str:
    """Coerce an emitted numeric expression to what the param kind requires.

    Mirrors `_bound_expr`: a float stays a float; a count is rounded, then
    clamped in the generated script so a live value can never detonate a union
    loop inside the render worker.
    """
    if kind == "float":
        return f"float({code})"
    if kind == "count":
        return f"min(max(int(round({code})), 1), {MAX_PATTERN_COUNT})"
    raise GraphError(f"{where}: {kind} params cannot be computed")  # pragma: no cover


def _resolved_param_default(pid: str, parameters: dict, where: str):
    """The transpile-time default for a manifest parameter id, or raise."""
    if pid not in parameters:
        raise GraphError(
            f"{where}: unknown parameter '{pid}' — declare it in the manifest's parameters[]"
        )
    value = parameters[pid]
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return value
    raise GraphError(f"{where}: parameter '{pid}' has no numeric default (got {value!r})")


def _expression_code(source, kind: str, parameters: dict, where: str) -> str:
    """Compile an `{"expr": ...}` param into emitted Python, or raise.

    Identifiers resolve to manifest parameters: each becomes the same
    `_param(lambda: pid, default)` probe a binding emits, so the expression is
    recomputed at render time from live values. An expression naming nothing
    live folds to a validated numeric literal instead.
    """
    if kind not in _BINDABLE_KINDS:
        raise GraphError(
            f"{where}: a {kind} param cannot be an expression — it must stay a literal"
        )
    if not isinstance(source, str):
        raise GraphError(f"{where}: 'expr' must be a string, got {type(source).__name__}")

    # Report every unknown identifier at once; the parser would stop at the first.
    try:
        names = expression_identifiers(source)
    except GraphExprError as exc:
        raise GraphError(f"{where}: invalid expression: {exc}") from exc
    unknown = [
        name for name in names
        if not is_emittable_identifier(name)
        or name not in parameters
        or _RESERVED_IDENTIFIERS.intersection({name})
    ]
    if unknown:
        raise GraphError(
            f"{where}: expression references unknown parameter(s) {sorted(set(unknown))} — "
            "identifiers must name a manifest parameter"
        )

    def resolve(name: str):
        default = _resolved_param_default(name, parameters, where)
        return (f"_param(lambda: {name}, {_literal_code(default)})", None)

    try:
        code, is_constant, constant = compile_expression(source, resolve)
    except GraphExprError as exc:
        raise GraphError(f"{where}: invalid expression: {exc}") from exc

    if is_constant:
        # Nothing live: validate the folded value against the param's own kind
        # so `{"expr": "0.5"}` on a count fails exactly like the literal would.
        return _literal(kind, _coerce_folded(kind, constant, where), where)
    return _numeric_wrapper(kind, code, where)


def _coerce_folded(kind: str, value, where: str):
    """A folded expression value, shaped for `_literal` of the given kind."""
    if isinstance(value, bool):
        raise GraphError(f"{where}: expression evaluates to a boolean, not a number")
    if kind == "count":
        if isinstance(value, float):
            if not value.is_integer():
                raise GraphError(
                    f"{where}: expression evaluates to {value}, but a count must be whole"
                )
            return int(value)
        return value
    return float(value)


def _literal_code(value) -> str:
    """A Python literal for a transpile-time default (bool stays bool)."""
    if isinstance(value, bool):
        return "True" if value else "False"
    return repr(value)


def _param_object_key(raw: dict, where: str) -> str:
    """The single key of a `{"param": …}` / `{"expr": …}` param value."""
    keys = set(raw)
    unknown = keys - _ALLOWED_PARAM_OBJECT_KEYS
    if unknown:
        raise GraphError(
            f"{where}: unknown keys {sorted(unknown)} — a param object is "
            f"{{'param': id}} or {{'expr': '...'}}"
        )
    if len(keys) != 1:
        raise GraphError(
            f"{where}: a param object needs exactly one of 'param' or 'expr' (got {sorted(keys)})"
        )
    return next(iter(keys))


def _param_reference_code(pid, kind: str, parameters: dict, where: str) -> str:
    """Emit an in-graph `{"param": id}` reference.

    Identical in effect to a manifest `binding`, written from the graph's side:
    the graph says which parameter drives the socket instead of the manifest
    reaching down. Same probe, same clamp, same restriction to numeric kinds.
    """
    if kind not in _BINDABLE_KINDS:
        raise GraphError(
            f"{where}: a {kind} param cannot reference a manifest parameter — "
            "it must stay a literal"
        )
    if not isinstance(pid, str) or not _IDENT_RE.match(pid) or keyword.iskeyword(pid):
        raise GraphError(f"{where}: 'param' must be a plain identifier (got {pid!r})")
    if pid.startswith("_") or pid in _RESERVED_IDENTIFIERS:
        raise GraphError(f"{where}: parameter '{pid}' collides with a reserved name")
    default = _resolved_param_default(pid, parameters, where)
    return _bound_expr(kind, pid, _literal(kind, _coerce_folded(kind, default, where), where), where)


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

    # Dangling references and socket-type agreement (both need every id known).
    for node_id, node in by_id.items():
        spec = NODE_TYPES[node["type"]]
        for socket, ref in node.get("inputs", {}).items():
            if ref not in by_id:
                raise GraphError(
                    f"{where}: node '{node_id}' input '{socket}' references unknown node '{ref}'"
                )
            wanted = spec["inputs"][socket]
            got = NODE_TYPES[by_id[ref]["type"]]["output"]
            if got != wanted:
                raise GraphError(
                    f"{where}: node '{node_id}' input '{socket}' wants a {wanted}, "
                    f"but '{ref}' is a {got}"
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

def parameter_defaults(manifest_parameters: list) -> dict:
    """Map manifest parameter id → its declared default, for expression use.

    Only numeric and boolean defaults are carried: an expression identifier
    must name something the dialect can hold. A parameter with a non-numeric
    default is simply absent, so an expression naming it fails as unknown
    rather than emitting a probe that would blow up at render time.
    """
    defaults: dict = {}
    for entry in manifest_parameters or []:
        pid = entry.get("id", "") if isinstance(entry, dict) else ""
        if not isinstance(pid, str) or not _IDENT_RE.match(pid) or keyword.iskeyword(pid):
            continue
        if pid.startswith("_") or pid in _RESERVED_IDENTIFIERS:
            continue
        value = entry.get("default")
        if isinstance(value, bool) or (
            isinstance(value, (int, float)) and math.isfinite(float(value))
        ):
            defaults[pid] = value
    return defaults


def transpile(
    doc: dict,
    bindings: dict | None = None,
    source_name: str = "graph",
    parameters: dict | None = None,
) -> str:
    """Compile a validated graph document into CadQuery script text.

    Deterministic: emission follows file order (topologically constrained), and
    every substituted value is a validated literal, a `_param` probe reading a
    manifest-bound parameter injected by cq_runner, or arithmetic over such
    probes compiled from an `{"expr": ...}` input. No character of the document
    is ever interpolated into the emitted script.

    `parameters` maps manifest parameter id → default (see
    `parameter_defaults`). Expression identifiers and `{"param": id}`
    references resolve against it; anything else is a hard error.
    """
    bindings = bindings or {}
    parameters = parameters if parameters is not None else {}
    _validate_document(doc, source_name)
    by_id = _validate_nodes(doc["nodes"], source_name)
    _validate_bindings(bindings, by_id, source_name)

    outputs = doc["outputs"]
    for part_id, ref in outputs.items():
        if not isinstance(part_id, str) or not part_id:
            raise GraphError(f"{source_name}: output part ids must be non-empty strings")
        if ref not in by_id:
            raise GraphError(f"{source_name}: output '{part_id}' references unknown node '{ref}'")
        if NODE_TYPES[by_id[ref]["type"]]["output"] != "solid":
            raise GraphError(
                f"{source_name}: output '{part_id}' is a profile; extrude it into a solid first"
            )

    # Emitted only when an expression actually needs it, so a graph that uses
    # no expressions transpiles to exactly the script it always did.
    uses_expressions = False

    def _param_expr(node: dict, name: str, kind: str, default) -> str:
        nonlocal uses_expressions
        where = f"{source_name}: node '{node['id']}' param '{name}'"
        raw = node.get("params", {}).get(name, default)

        # An object value is an in-graph reference or an expression. Either one
        # takes precedence over a manifest `binding` on the same target, and a
        # collision between the two is refused rather than silently ranked.
        if isinstance(raw, dict):
            key = _param_object_key(raw, where)
            if bindings.get((node["id"], name)) is not None:
                raise GraphError(
                    f"{where}: the graph sets this param with '{key}' but a manifest "
                    "parameter also binds it — use one or the other"
                )
            if key == _PARAM_EXPR_KEY:
                code = _expression_code(raw[key], kind, parameters, where)
                if "_expr_" in code:
                    uses_expressions = True
                return code
            return _param_reference_code(raw[key], kind, parameters, where)

        default_literal = _literal(kind, raw, where)
        pid = bindings.get((node["id"], name))
        if pid is None:
            return default_literal
        return _bound_expr(kind, pid, default_literal, where)

    body: list[str] = []
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
            rendered = spec["emit"](f"_n_{node['id']}", input_vars, param_exprs)
            body.extend([rendered] if isinstance(rendered, str) else rendered)
            emitted.add(node["id"])
            progressed = True
        if not progressed:
            cyclic = sorted(n["id"] for n in still)
            raise GraphError(f"{source_name}: dependency cycle among nodes {cyclic}")
        remaining = still

    default_part = next(iter(outputs))
    body.append("")
    body.append("_outputs = {")
    for part_id, ref in outputs.items():
        body.append(f"    {json.dumps(part_id)}: _n_{ref},")
    body.append("}")
    body.append(f"_target = str(_param(lambda: target_part, {json.dumps(default_part)}))")
    body.append("result = _outputs.get(_target)")
    body.append("if result is None:")
    body.append("    raise ValueError(\"Unknown target_part: \" + _target)")

    lines = [
        "# Generated by the Yantra4D graph engine - DO NOT EDIT.",
        f"# Source: {source_name}",
    ]
    if uses_expressions:
        lines.append("import math")
    lines.extend([
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
    ])
    if uses_expressions:
        lines.extend(EXPR_RUNTIME_LINES)
        lines.extend(["", ""])
    lines.extend(body)
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
    manifest_parameters = getattr(manifest, "parameters", None) or []
    bindings = extract_bindings(manifest_parameters)
    parameters = parameter_defaults(manifest_parameters)

    # The defaults join the key: an expression folds a parameter's default into
    # the emitted probe, so changing a default must produce a new script.
    fingerprint = hashlib.sha256(
        raw
        + json.dumps(sorted(bindings.items()), sort_keys=True).encode()
        + json.dumps(sorted(parameters.items()), sort_keys=True).encode()
    ).hexdigest()

    out_dir = Path(tempfile.gettempdir()) / "yantra4d_graphgen"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"graph_{fingerprint[:24]}.py"
    if out_path.is_file():
        return str(out_path)

    script = transpile(
        doc, bindings, source_name=os.path.basename(graph_path), parameters=parameters
    )

    tmp_path = out_path.with_suffix(".tmp")
    tmp_path.write_text(script)
    os.replace(tmp_path, out_path)
    logger.info("Transpiled graph %s -> %s", graph_path, out_path)
    return str(out_path)
