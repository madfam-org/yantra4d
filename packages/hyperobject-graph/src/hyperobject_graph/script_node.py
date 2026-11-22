"""The ``script`` node: a typed, sandboxed call to a cartridge's existing source.

RFC 0067 ruling G-1: every hyperobject gets a configurable graph now, as a **wrapper** —
one ``script`` node that runs the source the cartridge already has, with every parameter,
preset, constraint and interface declared by the graph. Native nodes replace it later,
by value, under the golden-twin rule. The node is the escape hatch too: a native graph
may keep a ``script`` node for work its vocabulary cannot express.

The node is owned by the core, not by a pack, so it means the same thing in all three
commons. A pack opts in by publishing a ``ScriptContract`` (languages, output types, the
name of its part parameter); the full contract is ``docs/GRAPH_CORE.md`` › "The script
node".

Shape (format 1.2)::

    {"id": "body", "type": "script",
     "params": {
       "source": "main.py",          # a file in the cartridge, relative, no ".."
       "language": "cadquery",       # one of the pack's script languages
       "output": "solid",            # one of the pack's script output socket types
       "bind": {                     # the source's parameter globals
         "width": {"param": "width"},       # pass the declared parameter through, raw
         "half":  {"expr": "width / 2"},    # a number or boolean in the 1.1 dialect
         "style": "round"                   # a literal: number, boolean or option value
       },
       "part": "lid"                 # optional: always render this part
     },
     "inputs": {}}

Semantics every kernel implements identically:

* **Pass-through is exact.** ``{"param": id}`` hands the source the injected value with
  its type unchanged (a select's string, a slider's number), and **absent stays absent**:
  when the render injects nothing for ``id``, the global is not defined, so the source's
  own fallback applies exactly as when it runs alone. This is what makes a wrapper render
  identically to the script it wraps at the defaults and at every preset.
* An ``expr`` or literal binding is always defined. An ``expr`` reads the graph's
  ``parameters``/``derived`` scope (1.1 semantics: injected value or declared default).
* **The part.** Without ``part`` the node passes the render's selected part (the pack's
  ``part_parameter``, ``target_part`` on solid) through unchanged, so one node serves every
  output that names it, and such a node may feed only ``outputs``. With ``part`` the node
  always renders that part and may feed other nodes.
* **No capability is added.** The source runs in the kernel's existing render sandbox,
  with the kernel's suffix gate, exactly as the cartridge's mode would run it. A wrapper is
  lowered by invoking that path, not by generating new code around the source.
* **Provenance.** Every script node's source appears in ``provenance.sources`` with its
  sha256, so an edit to the source without regenerating the graph is a visible drift.

``inputs`` is empty in contract v1: a script node consumes parameters, not upstream
sockets. Socket inputs (a solid handed to the source as a global) are a later version.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass

from .errors import GraphCoreError, Problem, as_dict, is_hashable_in
from .expression import evaluate, expression_names, parse_expression

SCRIPT_NODE_TYPE = "script"
#: The version of this contract. A kernel states which one it implements.
SCRIPT_CONTRACT_VERSION = "1.0"

SCRIPT_PARAMS = frozenset({"source", "language", "output", "bind", "part"})
SCRIPT_REQUIRED = frozenset({"source", "language", "output"})
#: How many globals one script node may bind (a convention: the commons' largest
#: manifests carry under 40 parameters).
MAX_SCRIPT_BINDINGS = 128
MAX_SOURCE_PATH = 200

IDENT_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
OPTION_RE = re.compile(r"^[A-Za-z0-9_.\- ]{0,64}$")
_PATH_SEGMENT_RE = re.compile(r"^[A-Za-z0-9_.\-]+$")

__all__ = [
    "SCRIPT_CONTRACT_VERSION",
    "SCRIPT_NODE_TYPE",
    "WrapperPlan",
    "coerce_parameter",
    "script_node_catalogue_entry",
    "script_node_problems",
    "wrapper_plan",
]


def script_node_catalogue_entry(contract) -> dict:
    """The ``script`` node as a catalogue entry, for an editor palette."""
    return {
        "output": {"one_of": list(contract.outputs)},
        "inputs": {},
        "params": {
            "source": {"kind": "path", "default": None, "bindable": False, "expr": False},
            "language": {"kind": "enum", "default": None, "bindable": False, "expr": False,
                         "one_of": sorted(contract.languages)},
            "output": {"kind": "enum", "default": None, "bindable": False, "expr": False,
                       "one_of": list(contract.outputs)},
            "bind": {"kind": "bindmap", "default": {}, "bindable": False, "expr": True},
            "part": {"kind": "option", "default": None, "bindable": False, "expr": False},
        },
        "contract": SCRIPT_CONTRACT_VERSION,
        "part_parameter": contract.part_parameter,
    }


def is_relative_source(path: object) -> bool:
    """A plain relative path inside the cartridge: no root, no ``..``, no backslash."""
    if not isinstance(path, str) or not path or len(path) > MAX_SOURCE_PATH:
        return False
    if path.startswith("/") or "\\" in path:
        return False
    return all(seg not in ("", ".", "..") and _PATH_SEGMENT_RE.match(seg)
               for seg in path.split("/"))


def _literal_ok(value: object) -> bool:
    if isinstance(value, bool):
        return True
    if isinstance(value, (int, float)):
        return math.isfinite(float(value))
    return isinstance(value, str) and bool(OPTION_RE.match(value))


def script_node_problems(
    node: dict,
    where: str,
    pack,
    *,
    declared_parameters: set[str] | None,
    expression_scope: set[str],
) -> tuple[list[Problem], set[str], set[str]]:
    """Check one script node against the contract and the pack's script contract.

    Returns ``(problems, parameters passed through, scope names read by expressions)``.
    ``declared_parameters`` is None when the graph has no ``declarations`` block, in
    which case a pass-through binding has nothing to name and is itself a problem.
    """
    problems: list[Problem] = []
    passed: set[str] = set()
    read: set[str] = set()
    contract = getattr(pack, "script", None)
    if contract is None:
        problems.append(Problem("script-node", where,
                                f"the {pack.name} pack declares no script contract"))
        return problems, passed, read

    params = node.get("params")
    if not isinstance(params, dict):
        problems.append(Problem("script-node", where, "'params' must be an object"))
        return problems, passed, read
    unknown = set(params) - SCRIPT_PARAMS
    if unknown:
        problems.append(Problem("script-node", where, f"unknown params: {sorted(unknown)}"))
    missing = SCRIPT_REQUIRED - set(params)
    if missing:
        problems.append(Problem("script-node", where, f"missing params: {sorted(missing)}"))
    if node.get("inputs"):
        problems.append(Problem(
            "script-node", where,
            "a script node takes parameters, not sockets: 'inputs' must be empty "
            f"(contract {SCRIPT_CONTRACT_VERSION})",
        ))

    language = params.get("language")
    source = params.get("source")
    if "language" in params and not is_hashable_in(language, contract.languages):
        problems.append(Problem(
            "script-node", where,
            f"language {language!r} is not one the {pack.name} pack runs "
            f"({sorted(contract.languages)})",
        ))
    if "source" in params:
        if not is_relative_source(source):
            problems.append(Problem(
                "script-node", where,
                f"source {source!r} must be a plain relative path inside the cartridge",
            ))
        elif is_hashable_in(language, contract.languages) and not any(
            source.endswith(sfx) for sfx in contract.languages[language]
        ):
            problems.append(Problem(
                "script-node", where,
                f"source {source!r} does not carry a {language} suffix "
                f"{list(contract.languages[language])}",
            ))
    output = params.get("output")
    if "output" in params and not is_hashable_in(output, contract.outputs):
        problems.append(Problem(
            "script-node", where,
            f"output {output!r} is not a type the {pack.name} pack lets a script yield "
            f"({list(contract.outputs)})",
        ))
    if "part" in params and not (isinstance(params["part"], str)
                                 and params["part"] and OPTION_RE.match(params["part"])):
        problems.append(Problem("script-node", where, "'part' must be a non-empty part id"))

    bind = params.get("bind", {})
    if not isinstance(bind, dict):
        problems.append(Problem("script-node", where, "'bind' must be an object"))
        return problems, passed, read
    if len(bind) > MAX_SCRIPT_BINDINGS:
        problems.append(Problem("script-node", where,
                                f"too many bindings ({len(bind)} > {MAX_SCRIPT_BINDINGS})"))
    for name, value in bind.items():
        loc = f"{where}/params/bind/{name}"
        if not isinstance(name, str) or not IDENT_RE.match(name):
            problems.append(Problem("script-node", loc, f"{name!r} is not a plain identifier"))
            continue
        if name == contract.part_parameter:
            problems.append(Problem(
                "script-node", loc,
                f"'{name}' is the pack's part parameter; it is passed through, or fixed "
                f"with 'part', never bound",
            ))
            continue
        if name in contract.reserved:
            problems.append(Problem(
                "script-node", loc,
                f"'{name}' is a name the {pack.name} runner defines for every source",
            ))
            continue
        if isinstance(value, dict) and set(value) == {"param"}:
            pid = value["param"]
            if declared_parameters is None:
                problems.append(Problem(
                    "script-node", loc,
                    "a pass-through binding needs a 'declarations' block to name",
                ))
            elif not is_hashable_in(pid, declared_parameters):
                problems.append(Problem(
                    "script-node", loc,
                    f"passes through {pid!r}, which 'declarations.parameters' does not declare",
                ))
            else:
                passed.add(pid)
        elif isinstance(value, dict) and "expr" in value:
            try:
                tree = parse_expression(value, loc)
            except GraphCoreError as exc:
                problems.append(Problem("expression", loc, str(exc)))
                continue
            names = expression_names(tree)
            unknown_names = sorted(names - expression_scope)
            if unknown_names:
                problems.append(Problem(
                    "expression", loc,
                    f"reads {unknown_names}, which the graph does not declare in "
                    f"'parameters' or 'derived'",
                ))
            read |= names
        elif not _literal_ok(value):
            problems.append(Problem(
                "script-node", loc,
                "a binding is {'param': id}, {'expr': ...}, or a number, boolean or "
                "option value",
            ))
    return problems, passed, read


def coerce_parameter(value, default, name: str, table: Mapping | None):
    """A graph parameter's value as the 1.1 dialect reads it (the engine's ``_g_in``).

    ``None`` takes the default; booleans stay booleans; numbers become floats; a string
    is looked up in the declared option ``map`` or read as decimal numeric text.
    """
    if value is None:
        value = default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        if table is not None and value in table:
            return float(table[value])
        text = value.strip()
        if text and "_" not in text and "x" not in text.lower():
            try:
                number = float(text)
            except ValueError:
                number = None
            if number is not None and math.isfinite(number):
                return number
    raise GraphCoreError(f"graph parameter {name} is not numeric: {value!r}",
                         code="expression")


def expression_env(doc: dict, injected: Mapping) -> dict:
    """The 1.1 expression scope: every ``parameters`` value, then each ``derived``."""
    env: dict = {}
    for pid, spec in (doc.get("parameters") or {}).items():
        env[pid] = coerce_parameter(injected.get(pid), spec.get("default"), pid,
                                    spec.get("map"))
    for entry in doc.get("derived") or []:
        env[entry["id"]] = evaluate(parse_expression(entry["expr"]), env)
    return env


@dataclass(frozen=True)
class WrapperPlan:
    """How a kernel renders a **pure wrapper**: one script node that every output names.

    A wrapper is not transpiled. The kernel renders ``source`` with ``language``'s
    existing path, in its existing sandbox, with ``script_params(injected)`` as the
    parameters — the same call the cartridge's mode makes, so the result is the script's.
    """

    node_id: str
    source: str
    language: str
    output: str
    bind: Mapping
    parts: tuple[str, ...]
    part_parameter: str
    doc: Mapping

    def script_params(self, injected: Mapping) -> dict:
        """The parameters the wrapped source receives for one render.

        ``injected`` is what the render would hand the graph: declared parameter values
        (the defaults render injects none) plus the pack's part parameter.
        """
        out: dict = {}
        env = None
        for name, value in self.bind.items():
            if isinstance(value, dict) and set(value) == {"param"}:
                if value["param"] in injected:
                    out[name] = injected[value["param"]]
            elif isinstance(value, dict) and "expr" in value:
                if env is None:
                    env = expression_env(dict(self.doc), injected)
                out[name] = evaluate(parse_expression(value), env)
            else:
                out[name] = value
        if self.part_parameter in injected:
            out[self.part_parameter] = injected[self.part_parameter]
        return out


def wrapper_plan(doc: dict, pack) -> WrapperPlan | None:
    """The lowering of a pure wrapper graph, or None when the graph is not one.

    Call it on a document ``validate`` accepted. A pure wrapper has exactly one node, a
    ``script`` node with no fixed ``part``, and every output names it.
    """
    nodes = doc.get("nodes") if isinstance(doc, dict) else None
    if not isinstance(nodes, list) or len(nodes) != 1 or not isinstance(nodes[0], dict) \
            or nodes[0].get("type") != SCRIPT_NODE_TYPE:
        return None
    node = nodes[0]
    params = as_dict(node.get("params"))
    if "part" in params or getattr(pack, "script", None) is None:
        return None
    if not all(isinstance(params.get(k), str) for k in ("source", "language", "output")):
        return None  # not a well-formed script node; validate says why
    outputs = as_dict(doc.get("outputs"))
    if not outputs or any(ref != node.get("id") for ref in outputs.values()):
        return None
    return WrapperPlan(
        node_id=node["id"],
        source=params["source"],
        language=params["language"],
        output=params["output"],
        bind=dict(as_dict(params.get("bind"))),
        parts=tuple(outputs),
        part_parameter=pack.script.part_parameter,
        doc=doc,
    )
