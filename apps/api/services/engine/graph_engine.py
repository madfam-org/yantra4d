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

Expressions (Wave D / G-EXPR, format 1.1): a numeric node param may be
`{"expr": "width / 2 - wall"}` in the restricted dialect the manifest constraints
use (apps/studio/src/lib/safeFormula.ts — arithmetic, comparison, boolean and
ternary over identifiers and numeric literals; no strings, no calls, at most 256
characters and 128 tokens). Identifiers are manifest parameter ids the graph
declares in a top-level `parameters` object (each with a fallback `default` and
an optional string→number `map` for non-numeric select options), or names from
the ordered top-level `derived` list. An expression is parsed and validated at
transpile time and re-emitted from its syntax tree as a closed arithmetic over
validated literals and parameter reads, so the security property is unchanged:
no document text is ever interpolated into the generated script.
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
# Pattern repeat ceiling. Each repeat is a boolean union, so an unbounded count
# is a denial-of-service against the render worker, not just a slow render.
MAX_PATTERN_COUNT = 200
# Expression limits: exactly the dialect's own (safeFormula.ts MAX_FORMULA_LENGTH /
# MAX_TOKENS), so a formula the Studio accepts is one the engine accepts.
MAX_EXPR_LENGTH = 256
MAX_EXPR_TOKENS = 128
# Document-size conventions (engine limits, not sourced facts): generous against the
# commons' largest manifests (under 20 parameters) and bounded so a document cannot
# make the transpiler or the generated preamble arbitrarily long.
MAX_GRAPH_PARAMETERS = 128
MAX_DERIVED = 256
MAX_MAP_ENTRIES = 64
MAX_POLYLINE_POINTS = 256
# Bounded revolve (G-NODES-2). Engine convention, not a sourced fact: a revolve
# profile may reach at most this far from the origin along the axis or across it.
# Commons parts are print-bed scale; anything larger is refused before the kernel
# is asked to build it.
MAX_REVOLVE_EXTENT = 1000.0
# How far a revolve profile may sit on the wrong side of its axis before it counts
# as crossing it (bounding-box round-off, not a design tolerance).
REVOLVE_AXIS_TOLERANCE = 1e-6

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

_ALLOWED_TOP_KEYS = frozenset({
    "version", "units", "nodes", "outputs", "meta", "parameters", "derived",
})
_ALLOWED_NODE_KEYS = frozenset({"id", "type", "params", "inputs", "meta"})
_ALLOWED_PARAMETER_KEYS = frozenset({"default", "map"})
_ALLOWED_DERIVED_KEYS = frozenset({"id", "expr"})
# A select option value (manifest `options[].value`) as a graph may name it: the
# charset is closed so json.dumps of it is always a plain Python string literal.
_OPTION_RE = re.compile(r"^[A-Za-z0-9_.\- ]{0,64}$")
# What a numeric string must look like to read as a number — the decimal subset of
# JavaScript's Number(): a non-decimal or underscored spelling is refused, not parsed.
_NUMERIC_TEXT_RE = re.compile(r"^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$")

_AXIS_TUPLES = {"x": "(1, 0, 0)", "y": "(0, 1, 0)", "z": "(0, 0, 1)"}
_PLANES = frozenset({"XY", "XZ", "YZ"})
# Which world axes lie in each workplane: a revolve axis must lie in its profile's
# plane, or the result is a zero-volume solid that still reports itself valid.
_PLANE_AXES = {"XY": frozenset({"x", "y"}), "XZ": frozenset({"x", "z"}), "YZ": frozenset({"y", "z"})}


class GraphError(ValueError):
    """Raised when a graph document fails validation or transpilation."""


def _source_comment_text(source_name) -> str:
    """The source name as it is written into the generated script's header comment.

    The name is the one piece of text the engine does not take from validated
    values, so it is written as an escaped literal: a backslash, and every
    character `str.isprintable()` rejects (every line terminator Python or
    `str.splitlines()` recognises, `\\r\\n`, form feed, NUL, U+2028/U+2029, and every
    other control, format, separator or surrogate character), is written as its
    Python escape sequence. The comment therefore stays on one line whatever the
    name holds. A plain printable name is written unchanged.
    """
    text = str(source_name)
    if text.isprintable() and "\\" not in text:
        return text
    return "".join(
        ch if ch.isprintable() and ch != "\\" else repr(ch)[1:-1] for ch in text
    )


# ── Node vocabulary ────────────────────────────────────────────────────────────
# Each type declares typed params (kind, default), typed input sockets
# ({socket: required_output_type}), and its own output type — "solid" or
# "profile" (a 2D sketch that only extrude consumes). Emitters receive
# already-safe expression strings: a param expression is always either a
# validated literal or a `_param(...)` probe, never raw text. An emitter
# returns one line or a list of lines.
#
# revolve returned in Wave D (G-NODES-2) only in BOUNDED form. During vocabulary
# bring-up a 360° revolve exhausted memory and killed the process. That run is
# not reproducible on CadQuery 2.7 (a profile straddling its axis now fails fast
# in OCC), so the bound is on the inputs that decide a revolve's cost and
# validity: the angle is (0, 360] (OCC silently wraps larger angles), the axis
# must lie in the profile's plane (checked at transpile time; otherwise the result
# is a zero-volume "valid" solid), the profile may not cross the axis, and it may
# reach at most MAX_REVOLVE_EXTENT from the origin. All of that is checked before
# the kernel is called (see _REVOLVE_HELPER), and the result must be a valid solid
# with positive volume before anything consumes it.

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


def _emit_profile_polyline(v, i, p):
    return f"{v} = cq.Workplane({p['plane']}).polyline({p['points']}).close()"


def _emit_extrude(v, i, p):
    return f"{v} = {i['profile']}.extrude({p['height']})"


def _emit_revolve(v, i, p):
    # The axis tuple and the node id are both validated literals; the helper does
    # every runtime bound before OCC is called.
    return f"{v} = _g_revolve({i['profile']}, {p['angle']}, {p['axis']}, {json.dumps(v[3:])})"


def _emit_reflect(v, i, p):
    # A pure reflection. `mirror` (below) keeps the original too, which is a
    # different operation — a handed part needs the reflection alone.
    return f"{v} = {i['shape']}.mirror({p['plane']})"


def _emit_select(v, i, p):
    # Both inputs are built (emission is eager and topological); the condition only
    # chooses which one flows on. A branch that cannot be built fails the render even
    # when it is not chosen — loud by design.
    return f"{v} = {i['if_true']} if {p['when']} else {i['if_false']}"


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
# "plane" (XY|XZ|YZ workplane name), "condition" (a boolean; `select` reads it), and
# "points" (a list of [x, y] pairs, 3..MAX_POLYLINE_POINTS). float, count and
# condition accept an {"expr": ...}; each coordinate of a points list does too.
# PARAM_KINDS (below the vocabulary) is the per-kind contract the catalog publishes.
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
    "profile_polyline": {
        "params": {
            "points": ("points", [[0.0, 0.0], [10.0, 0.0], [0.0, 10.0]]),
            "plane": ("plane", "XY"),
        },
        "inputs": {},
        "output": "profile",
        "emit": _emit_profile_polyline,
    },
    "extrude": {
        "params": {"height": ("float", 10.0)},
        "inputs": {"profile": "profile"},
        "output": "solid",
        "emit": _emit_extrude,
    },
    "revolve": {
        "params": {"angle": ("float", 360.0), "axis": ("axis", "z")},
        "inputs": {"profile": "profile"},
        "output": "solid",
        "emit": _emit_revolve,
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
    "reflect": {
        "params": {"plane": ("plane", "YZ")},
        "inputs": {"shape": "solid"},
        "output": "solid",
        "emit": _emit_reflect,
    },
    # ── Selection ─────────────────────────────────────────────────────────────
    "select": {
        "params": {"when": ("condition", True)},
        "inputs": {"if_true": "solid", "if_false": "solid"},
        "output": "solid",
        "emit": _emit_select,
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


# The per-kind contract, published in the catalog so an editor can render an input
# for a kind it has never seen: whether a manifest parameter may bind it, whether it
# takes an {"expr": ...}, and what a literal value looks like.
PARAM_KINDS = {
    "float": {"bindable": True, "expr": True, "literal": "number"},
    "count": {"bindable": True, "expr": True, "literal": "integer"},
    "condition": {"bindable": False, "expr": True, "literal": "boolean"},
    "points": {"bindable": False, "expr": True, "literal": "array of [x, y] number pairs"},
    "selector": {"bindable": False, "expr": False, "literal": "string"},
    "axis": {"bindable": False, "expr": False, "literal": "x | y | z"},
    "plane": {"bindable": False, "expr": False, "literal": "XY | XZ | YZ"},
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


def _condition_literal(value, where: str) -> str:
    if not isinstance(value, bool):
        raise GraphError(f"{where}: expected true or false (or an expression)")
    return repr(value)


def _literal(kind: str, value, where: str) -> str:
    if kind == "condition":
        return _condition_literal(value, where)
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
    if kind in ("selector", "axis", "plane", "condition", "points"):
        raise GraphError(f"{where}: {kind} params cannot be bound to manifest parameters")
    raise GraphError(f"{where}: unknown param kind {kind!r}")  # pragma: no cover


# ── Expressions (G-EXPR) ──────────────────────────────────────────────────────
# A mirror of apps/studio/src/lib/safeFormula.ts: the same tokens, the same
# precedence (ternary < || < && < comparison < additive < multiplicative < unary),
# the same limits, and the same value semantics. Values are JavaScript numbers or
# booleans, carried as Python floats and bools:
#   * arithmetic and ordering coerce through Number() (true → 1);
#   * == / === and != / !== are STRICT (a boolean never equals a number);
#   * && and || return booleans, and like the Studio evaluator they evaluate both
#     sides, as a ternary evaluates both branches — an error in either is an error;
#   * / and % by zero are errors, % is the truncating remainder (math.fmod);
#   * truthiness is JavaScript's (0 and NaN are false).
# The parser builds a syntax tree; the emitter re-spells it as Python over validated
# float literals, `_g_p_<id>` / `_g_d_<id>` reads and a fixed set of helper calls.
# Nothing from the expression's text reaches the generated script.

_EXPR_OPERATORS = (
    "===", "!==", "<=", ">=", "&&", "||", "==", "!=", "+", "-", "*", "/", "%", "<", ">", "!",
)
_EXPR_COMPARISON = frozenset({"<", "<=", ">", ">=", "==", "!=", "===", "!=="})
# CPython refuses source nested more than 200 brackets deep; stay clear of it.
_MAX_EMITTED_NESTING = 150


def _expr_tokenize(source: str, where: str) -> list:
    if len(source) > MAX_EXPR_LENGTH:
        raise GraphError(f"{where}: expression is too long (max {MAX_EXPR_LENGTH} characters)")
    tokens: list = []
    index = 0
    length = len(source)
    while index < length:
        char = source[index]
        if char.isspace():
            index += 1
            continue
        nxt = source[index + 1] if index + 1 < length else ""
        if "0" <= char <= "9" or (char == "." and "0" <= nxt <= "9"):
            start = index
            index += 1
            while index < length and "0" <= source[index] <= "9":
                index += 1
            if index < length and source[index] == ".":
                index += 1
                while index < length and "0" <= source[index] <= "9":
                    index += 1
            tokens.append(("number", source[start:index]))
            continue
        if char.isascii() and (char.isalpha() or char in "_$"):
            start = index
            index += 1
            while index < length and source[index].isascii() and (
                source[index].isalnum() or source[index] in "_$"
            ):
                index += 1
            tokens.append(("identifier", source[start:index]))
            continue
        if char in "()?:":
            tokens.append((char, char))
            index += 1
            continue
        operator = next((op for op in _EXPR_OPERATORS if source.startswith(op, index)), None)
        if operator is None:
            raise GraphError(f"{where}: unsupported token {char!r} in expression")
        tokens.append(("operator", operator))
        index += len(operator)
    if len(tokens) > MAX_EXPR_TOKENS:
        raise GraphError(f"{where}: expression has too many tokens (max {MAX_EXPR_TOKENS})")
    tokens.append(("eof", ""))
    return tokens


class _ExprParser:
    """Recursive descent, one method per safeFormula.ts method, in the same order."""

    def __init__(self, source: str, where: str):
        self.where = where
        self.tokens = _expr_tokenize(source, where)
        self.cursor = 0

    def fail(self, message: str):
        raise GraphError(f"{self.where}: {message} in expression")

    def current(self):
        return self.tokens[self.cursor]

    def match(self, *values):
        kind, value = self.current()
        if kind != "operator" or value not in values:
            return None
        self.cursor += 1
        return value

    def parse(self):
        tree = self.conditional()
        if self.current()[0] != "eof":
            self.fail("unexpected trailing token")
        return tree

    def conditional(self):
        condition = self.logical_or()
        if self.current()[0] != "?":
            return condition
        self.cursor += 1
        when_true = self.conditional()
        if self.current()[0] != ":":
            self.fail("expected conditional separator")
        self.cursor += 1
        when_false = self.conditional()
        return ("if", condition, when_true, when_false)

    def logical_or(self):
        left = self.logical_and()
        while self.match("||"):
            left = ("or", left, self.logical_and())
        return left

    def logical_and(self):
        left = self.comparison()
        while self.match("&&"):
            left = ("and", left, self.comparison())
        return left

    def comparison(self):
        left = self.additive()
        while self.current()[0] == "operator" and self.current()[1] in _EXPR_COMPARISON:
            operator = self.current()[1]
            self.cursor += 1
            left = ("compare", operator, left, self.additive())
        return left

    def additive(self):
        left = self.multiplicative()
        while True:
            operator = self.match("+", "-")
            if operator is None:
                return left
            left = ("arith", operator, left, self.multiplicative())

    def multiplicative(self):
        left = self.unary()
        while True:
            operator = self.match("*", "/", "%")
            if operator is None:
                return left
            left = ("arith", operator, left, self.unary())

    def unary(self):
        operator = self.match("!", "-", "+")
        if operator is not None:
            return ("unary", operator, self.unary())
        return self.primary()

    def primary(self):
        kind, value = self.current()
        if kind == "number":
            self.cursor += 1
            number = float(value)
            if not math.isfinite(number):
                self.fail("invalid number")
            return ("number", number)
        if kind == "identifier":
            self.cursor += 1
            return ("name", value)
        if kind == "(":
            self.cursor += 1
            tree = self.conditional()
            if self.current()[0] != ")":
                self.fail("expected closing parenthesis")
            self.cursor += 1
            return tree
        self.fail("expected value")
        return None  # pragma: no cover - fail() raises


def _expr_names(tree) -> set:
    """Every identifier a syntax tree reads."""
    if tree[0] == "name":
        return {tree[1]}
    if tree[0] == "number":
        return set()
    names: set = set()
    for child in tree[1:]:
        if isinstance(child, tuple):
            names |= _expr_names(child)
    return names


def _emit_expr_tree(tree, scope: dict) -> str:
    """Python for a syntax tree. `scope` maps an identifier to its script variable."""
    head = tree[0]
    if head == "number":
        return repr(tree[1])
    if head == "name":
        return scope[tree[1]]
    if head == "unary":
        inner = _emit_expr_tree(tree[2], scope)
        if tree[1] == "!":
            return f"(not _g_truth({inner}))"
        if tree[1] == "-":
            return f"(-float({inner}))"
        return f"float({inner})"
    if head == "arith":
        left = _emit_expr_tree(tree[2], scope)
        right = _emit_expr_tree(tree[3], scope)
        if tree[1] == "/":
            return f"_g_div({left}, {right})"
        if tree[1] == "%":
            return f"_g_mod({left}, {right})"
        return f"(float({left}) {tree[1]} float({right}))"
    if head == "compare":
        left = _emit_expr_tree(tree[2], scope)
        right = _emit_expr_tree(tree[3], scope)
        if tree[1] in ("==", "==="):
            return f"_g_eq({left}, {right})"
        if tree[1] in ("!=", "!=="):
            return f"(not _g_eq({left}, {right}))"
        return f"(float({left}) {tree[1]} float({right}))"
    if head == "and":
        return f"_g_and({_emit_expr_tree(tree[1], scope)}, {_emit_expr_tree(tree[2], scope)})"
    if head == "or":
        return f"_g_or({_emit_expr_tree(tree[1], scope)}, {_emit_expr_tree(tree[2], scope)})"
    # "if"
    parts = ", ".join(_emit_expr_tree(child, scope) for child in tree[1:])
    return f"_g_if({parts})"


def _nesting(text: str) -> int:
    depth = deepest = 0
    for char in text:
        if char == "(":
            depth += 1
            deepest = max(deepest, depth)
        elif char == ")":
            depth -= 1
    return deepest


class _ExprScope:
    """The identifiers expressions may read, and which of them were read."""

    def __init__(self):
        self.variables: dict[str, str] = {}
        self.used: set[str] = set()
        self.compiled = 0

    def compile(self, value, where: str) -> str:
        if not isinstance(value, dict) or set(value) != {"expr"}:
            raise GraphError(f"{where}: an expression must be an object with one key, 'expr'")
        source = value["expr"]
        if not isinstance(source, str) or not source.strip():
            raise GraphError(f"{where}: 'expr' must be a non-empty string")
        tree = _ExprParser(source, where).parse()
        unknown = sorted(_expr_names(tree) - set(self.variables))
        if unknown:
            raise GraphError(
                f"{where}: expression reads {unknown}, which the graph does not declare in "
                f"'parameters' or 'derived' (declared: {sorted(self.variables)})"
            )
        self.used |= _expr_names(tree)
        self.compiled += 1
        emitted = _emit_expr_tree(tree, self.variables)
        if _nesting(emitted) > _MAX_EMITTED_NESTING:
            raise GraphError(f"{where}: expression nests too deeply")
        return emitted


def _is_expr(value) -> bool:
    return isinstance(value, dict) and "expr" in value


def _numeric_text(value: str):
    """The number a numeric option string spells, or None (safeFormula reads these)."""
    text = value.strip()
    if not _NUMERIC_TEXT_RE.match(text):
        return None
    number = float(text)
    return number if math.isfinite(number) else None


def _identifier_rules(name, where: str) -> None:
    if not isinstance(name, str) or not _IDENT_RE.match(name) or keyword.iskeyword(name):
        raise GraphError(f"{where}: {name!r} is not a plain identifier")
    if name in _RESERVED_IDENTIFIERS:
        raise GraphError(f"{where}: {name!r} collides with a reserved name")


def _compile_parameters(doc: dict, scope: _ExprScope, where: str) -> list:
    """Validate `parameters` and return the lines that read them."""
    declared = doc.get("parameters", {})
    if not isinstance(declared, dict):
        raise GraphError(f"{where}: 'parameters' must be an object of parameter id → declaration")
    if len(declared) > MAX_GRAPH_PARAMETERS:
        raise GraphError(f"{where}: too many parameters ({len(declared)} > {MAX_GRAPH_PARAMETERS})")
    lines = []
    for pid, spec in declared.items():
        loc = f"{where}: parameter '{pid}'"
        _identifier_rules(pid, loc)
        if not isinstance(spec, dict) or "default" not in spec:
            raise GraphError(f"{loc}: must be an object with a 'default'")
        unknown = set(spec) - _ALLOWED_PARAMETER_KEYS
        if unknown:
            raise GraphError(f"{loc}: unknown keys: {sorted(unknown)}")
        table = spec.get("map")
        table_literal = "None"
        if table is not None:
            if not isinstance(table, dict) or not table or len(table) > MAX_MAP_ENTRIES:
                raise GraphError(f"{loc}: 'map' must be an object of 1..{MAX_MAP_ENTRIES} entries")
            entries = []
            for option, number in table.items():
                if not _OPTION_RE.match(option):
                    raise GraphError(f"{loc}: map key {option!r} is not a plain option value")
                entries.append(f"{json.dumps(option)}: {_float_literal(number, f'{loc} map {option!r}')}")
            table_literal = "{" + ", ".join(entries) + "}"
        default = spec["default"]
        if isinstance(default, bool):
            default_literal = repr(default)
        elif isinstance(default, (int, float)):
            default_literal = _float_literal(default, f"{loc} default")
        elif isinstance(default, str) and _OPTION_RE.match(default):
            if _numeric_text(default) is None and default not in (table or {}):
                raise GraphError(f"{loc}: default {default!r} is neither numeric nor in 'map'")
            default_literal = json.dumps(default)
        else:
            raise GraphError(f"{loc}: default must be a number, a boolean or an option value")
        variable = f"_g_p_{pid}"
        scope.variables[pid] = variable
        lines.append(
            f"{variable} = _g_in(_param(lambda: {pid}, None), {default_literal}, "
            f"{json.dumps(pid)}, {table_literal})"
        )
    return lines


def _compile_derived(doc: dict, scope: _ExprScope, where: str) -> list:
    """Validate `derived` (in order: each may read parameters and earlier entries)."""
    derived = doc.get("derived", [])
    if not isinstance(derived, list):
        raise GraphError(f"{where}: 'derived' must be an array of {{id, expr}}")
    if len(derived) > MAX_DERIVED:
        raise GraphError(f"{where}: too many derived values ({len(derived)} > {MAX_DERIVED})")
    lines = []
    for idx, entry in enumerate(derived):
        loc = f"{where}: derived[{idx}]"
        if not isinstance(entry, dict) or set(entry) != _ALLOWED_DERIVED_KEYS:
            raise GraphError(f"{loc}: must be an object with exactly 'id' and 'expr'")
        name = entry["id"]
        _identifier_rules(name, loc)
        if name in scope.variables:
            raise GraphError(f"{loc}: '{name}' is already declared")
        emitted = scope.compile({"expr": entry["expr"]}, f"{loc} '{name}'")
        variable = f"_g_d_{name}"
        scope.variables[name] = variable
        lines.append(f"{variable} = {emitted}")
    return lines


# The runtime half of the expression semantics, emitted only into scripts that use
# expressions (a 1.0 graph transpiles byte-for-byte as before). Every function is
# plain arithmetic over floats and bools; `_g_in` is the one place a raw injected
# value is turned into a number, by the same rules safeFormula.ts applies to a
# parameter (numbers and booleans as-is, numeric strings parsed) plus the graph's
# declared option map.
_EXPR_HELPERS = '''import math


def _g_in(value, default, name, table):
    if value is None:
        value = default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        if table is not None and value in table:
            return table[value]
        text = value.strip()
        if text and "_" not in text and "x" not in text.lower():
            try:
                number = float(text)
            except ValueError:
                number = None
            if number is not None and math.isfinite(number):
                return number
    raise ValueError("graph parameter " + name + " is not numeric: " + repr(value))


def _g_truth(value):
    return bool(value) and value == value


def _g_eq(left, right):
    return type(left) is type(right) and left == right


def _g_and(left, right):
    return _g_truth(left) and _g_truth(right)


def _g_or(left, right):
    return _g_truth(left) or _g_truth(right)


def _g_if(condition, when_true, when_false):
    return when_true if _g_truth(condition) else when_false


def _g_div(left, right):
    right = float(right)
    if right == 0:
        raise ZeroDivisionError("Division by zero")
    return float(left) / right


def _g_mod(left, right):
    right = float(right)
    if right == 0:
        raise ZeroDivisionError("Division by zero")
    left = float(left)
    if not math.isfinite(left):
        return math.nan
    return math.fmod(left, right)


def _g_float(value, where):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(where + ": expression is not a finite number")
    return number


def _g_count(value, where):
    return min(max(int(_g_float(value, where)), 1), {max_count})
'''.replace("{max_count}", str(MAX_PATTERN_COUNT))


_REVOLVE_HELPER = '''def _g_revolve(profile, angle, axis, where):
    angle = float(angle)
    if not 0.0 < angle <= 360.0:
        raise ValueError(where + ": revolve angle must be in (0, 360] degrees, got " + repr(angle))
    direction = cq.Vector(axis[0], axis[1], axis[2])
    across = profile.plane.zDir.cross(direction)
    box = cq.Compound.makeCompound(profile.vals()).BoundingBox()
    corners = [cq.Vector(x, y, z) for x in (box.xmin, box.xmax)
               for y in (box.ymin, box.ymax) for z in (box.zmin, box.zmax)]
    radial = [across.dot(c) for c in corners]
    axial = [direction.dot(c) for c in corners]
    if min(radial) < -{tol} and max(radial) > {tol}:
        raise ValueError(where + ": revolve profile crosses its axis")
    if max(abs(v) for v in radial + axial) > {extent}:
        raise ValueError(where + ": revolve profile reaches beyond {extent} mm")
    start = profile.plane.toLocalCoords(cq.Vector(0, 0, 0))
    end = profile.plane.toLocalCoords(direction)
    solid = profile.revolve(angle, (start.x, start.y), (end.x, end.y))
    shape = solid.val()
    if not shape.isValid() or not shape.Volume() > 0:
        raise ValueError(where + ": revolve did not produce a valid solid")
    return solid
'''.replace("{tol}", repr(REVOLVE_AXIS_TOLERANCE)).replace("{extent}", repr(MAX_REVOLVE_EXTENT))


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
    profile_consumers: dict[str, str] = {}
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
            # A profile is a CadQuery workplane holding PENDING wires, and the first
            # extrude/revolve consumes them: a second consumer fails at render with
            # "No pending wires present". Refuse it here, where the author can see it.
            if got == "profile":
                consumer = profile_consumers.setdefault(ref, node_id)
                if consumer != node_id:
                    raise GraphError(
                        f"{where}: profile '{ref}' feeds both '{consumer}' and '{node_id}'; "
                        f"a profile can feed one node — duplicate the profile node"
                    )
            # A revolve axis must lie in its profile's plane (the plane is a literal,
            # so this is decidable here).
            if node["type"] == "revolve":
                axis = node.get("params", {}).get("axis", spec["params"]["axis"][1])
                plane = by_id[ref].get("params", {}).get("plane", "XY")
                if plane in _PLANE_AXES and axis in _AXIS_TUPLES and axis not in _PLANE_AXES[plane]:
                    raise GraphError(
                        f"{where}: node '{node_id}' revolves about {axis}, which is normal to "
                        f"its profile's {plane} plane; the axis must lie in the plane"
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
        if NODE_TYPES[by_id[ref]["type"]]["output"] != "solid":
            raise GraphError(
                f"{source_name}: output '{part_id}' is a profile; extrude it into a solid first"
            )

    scope = _ExprScope()
    declaration_lines = _compile_parameters(doc, scope, source_name)
    declaration_lines += _compile_derived(doc, scope, source_name)

    def _expression(raw, kind: str, where: str, tag: str) -> str:
        if kind not in ("float", "count", "condition"):
            raise GraphError(f"{where}: {kind} params take literal values, not expressions")
        emitted = scope.compile(raw, where)
        if kind == "float":
            return f"_g_float({emitted}, {json.dumps(tag)})"
        if kind == "count":
            return f"_g_count({emitted}, {json.dumps(tag)})"
        return f"_g_truth({emitted})"

    def _points_expr(node: dict, raw, where: str) -> str:
        if not isinstance(raw, list) or not 3 <= len(raw) <= MAX_POLYLINE_POINTS:
            raise GraphError(f"{where}: expected 3..{MAX_POLYLINE_POINTS} [x, y] points")
        pairs = []
        for idx, point in enumerate(raw):
            if not isinstance(point, list) or len(point) != 2:
                raise GraphError(f"{where}: point {idx} must be an [x, y] pair")
            coords = []
            for axis_idx, value in enumerate(point):
                tag = f"{node['id']}.points[{idx}][{axis_idx}]"
                if _is_expr(value):
                    coords.append(_expression(value, "float", f"{where} point {idx}", tag))
                else:
                    coords.append(_float_literal(value, f"{where} point {idx}"))
            pairs.append(f"({coords[0]}, {coords[1]})")
        return "[" + ", ".join(pairs) + "]"

    def _param_expr(node: dict, name: str, kind: str, default) -> str:
        where = f"{source_name}: node '{node['id']}' param '{name}'"
        raw = node.get("params", {}).get(name, default)
        pid = bindings.get((node["id"], name))
        if kind == "points" and pid is not None:
            _bound_expr(kind, pid, "", where)  # raises: points are never bindable
        if _is_expr(raw) or kind == "points":
            if pid is not None:
                raise GraphError(
                    f"{where}: bound to manifest parameter '{pid}' and also carries an "
                    f"expression; a node param takes one or the other"
                )
            if kind == "points":
                return _points_expr(node, raw, where)
            return _expression(raw, kind, where, f"{node['id']}.{name}")
        default_literal = _literal(kind, raw, where)
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

    # A declared name nothing reads is a control wired to nothing — the dead-parameter
    # bug a graph is meant to be unable to have (G-DEADPARAM).
    unread = sorted(set(scope.variables) - scope.used)
    if unread:
        raise GraphError(
            f"{source_name}: declared but never read by any expression: {unread}"
        )

    lines = [
        "# Generated by the Yantra4D graph engine - DO NOT EDIT.",
        f"# Source: {_source_comment_text(source_name)}",
        "import cadquery as cq",
    ]
    # Helpers are emitted only into scripts that need them, so a graph that uses
    # neither expressions nor revolve transpiles exactly as it did before Wave D.
    if scope.compiled:
        lines.extend(_EXPR_HELPERS.splitlines())
    lines.extend([
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
    if any(node["type"] == "revolve" for node in by_id.values()):
        lines.extend(_REVOLVE_HELPER.splitlines())
        lines.extend(["", ""])
    if declaration_lines:
        lines.extend(declaration_lines)
        lines.append("")
    lines.extend(body)

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
