"""Validating a graph document against the core and a node pack, and handing it on.

``validate(doc, pack)`` returns every problem it finds, so an editor can show them all at
once; ``check`` raises on the first batch; ``transpile`` validates and hands the pack the
document with the core-only keys removed.

What is checked here, for every kernel alike:

* the document: ``version`` (1.x), ``units``, the allowed top-level keys per format, a
  ``kernel`` that matches the pack, caps on nodes and outputs;
* nodes: plain unique ids, known types, known params, known input sockets;
* the graph: dangling references, socket types, fan-out limits, **cycles**, **unbound
  inputs** (a required socket with nothing connected), outputs that reference a node
  of an output type;
* bindings: a ``binding`` targets a node param that exists and whose kind is bindable,
  and a bound param does not also carry an expression;
* expressions (format 1.1): ``parameters`` and ordered ``derived`` declarations, every
  ``{"expr"}`` parsed in the dialect and reading only declared names, every declared
  name read, and an expression only where the param's kind takes one;
* format 1.2: the ``script`` node contract, ``declarations``, ``licence``, ``provenance``.

What is not: literal value ranges and anything geometric. Those are the pack's, and its
transpiler refuses them with its own message.
"""

from __future__ import annotations

import keyword
import math
import re

from .declarations import (
    declaration_problems,
    declared_bindings,
    declared_parameter_ids,
)
from .errors import GraphCoreError, Problem, as_dict, is_hashable_in
from .expression import expression_names, is_expression, parse_expression
from .pack import KERNELS
from .provenance import provenance_problems
from .script_node import (
    IDENT_RE,
    OPTION_RE,
    SCRIPT_NODE_TYPE,
    script_node_problems,
    wrapper_plan,
)

#: Graph format versions: 1.0 (nodes), 1.1 (expressions), 1.2 (core: kernel,
#: declarations, licence, provenance, the script node).
VERSION_RE = re.compile(r"^1\.(\d+)(\.\d+)?$")
FORMAT_VERSION = "1.2"
FORMAT_MINOR = 2
PACK_KEYS = frozenset({"version", "units", "nodes", "outputs", "meta", "parameters", "derived"})
CORE_KEYS = frozenset({"kernel", "declarations", "licence", "provenance"})
NODE_KEYS = frozenset({"id", "type", "params", "inputs", "meta"})
PARAMETER_KEYS = frozenset({"default", "map"})
UNITS = frozenset({"mm"})
# Document-size conventions, the solid engine's own so no document passes one and fails
# the other: engine limits, not sourced facts.
MAX_NODES = 500
MAX_OUTPUTS = 50
MAX_PARAMETERS = 128
MAX_DERIVED = 256
MAX_MAP_ENTRIES = 64
_BINDING_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)$")
_NUMERIC_TEXT_RE = re.compile(r"^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$")

__all__ = [
    "CORE_KEYS",
    "FORMAT_VERSION",
    "PACK_KEYS",
    "binding_parameters",
    "check",
    "extract_bindings",
    "format_minor",
    "pack_document",
    "transpile",
    "validate",
]


def format_minor(doc: object) -> int | None:
    """The minor of a 1.x ``version``, or None when it is not one."""
    version = doc.get("version") if isinstance(doc, dict) else None
    m = VERSION_RE.match(version) if isinstance(version, str) else None
    return int(m.group(1)) if m else None


def extract_bindings(parameters: list, reserved: frozenset[str] = frozenset()) -> dict:
    """``(node id, param) → parameter id`` from ``binding`` entries.

    The semantics of the solid engine's ``extract_bindings``: a binding is one
    ``"node.param"`` or a list of them; a target is bound by at most one parameter; the
    parameter id is a plain identifier that shadows nothing.
    """
    bindings: dict[tuple[str, str], str] = {}
    for entry in parameters or []:
        binding = entry.get("binding") if isinstance(entry, dict) else None
        if not binding:
            continue
        pid = entry.get("id", "")
        if not isinstance(pid, str) or not IDENT_RE.match(pid) or keyword.iskeyword(pid):
            raise GraphCoreError(
                f"parameter '{pid}': id is not bindable (must be a plain identifier)",
                code="binding",
            )
        if pid in reserved:
            raise GraphCoreError(f"parameter '{pid}': id collides with a reserved name",
                                 code="binding")
        for target in binding if isinstance(binding, list) else [binding]:
            m = _BINDING_RE.match(target) if isinstance(target, str) else None
            if not m:
                raise GraphCoreError(
                    f"parameter '{pid}': invalid binding {target!r} (want 'nodeId.param')",
                    code="binding",
                )
            key = (m.group(1), m.group(2))
            if key in bindings:
                raise GraphCoreError(
                    f"binding target {target!r} is bound by more than one parameter",
                    code="binding",
                )
            bindings[key] = pid
    return bindings


def binding_parameters(doc: dict, manifest_parameters: list | None) -> list:
    """The parameter list a graph's ``binding`` map is read from: its declarations when
    it has them (format 1.2), else the manifest's (1.0/1.1 graphs bind from there)."""
    if isinstance(doc.get("declarations"), dict):
        return declared_bindings(doc)
    return list(manifest_parameters or [])


def pack_document(doc: dict) -> dict:
    """The document a pack transpiles: the core-only keys removed, nothing else touched.

    For a 1.0 or 1.1 document this is the document itself, key for key, which is what
    keeps every existing graph's transpile byte-identical behind the interface.
    """
    return {k: v for k, v in doc.items() if k not in CORE_KEYS}


def _spec_of(catalogue, node: dict):
    ntype = node.get("type")
    return catalogue.get(ntype) if isinstance(ntype, str) else None


def _identifier_problem(name: object, where: str, reserved: frozenset[str]) -> Problem | None:
    if not isinstance(name, str) or not IDENT_RE.match(name) or keyword.iskeyword(name):
        return Problem("identifier", where, f"{name!r} is not a plain identifier")
    if name in reserved:
        return Problem("identifier", where, f"{name!r} collides with a reserved name")
    return None


def _walk_exprs(value):
    """Every ``{"expr"}`` object anywhere inside a param value."""
    if is_expression(value):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _walk_exprs(item)


def _numeric_text(value: str) -> bool:
    return bool(_NUMERIC_TEXT_RE.match(value.strip()))


def validate(
    doc: object,
    pack,
    *,
    parameters: list | None = None,
) -> list[Problem]:
    """Every problem with ``doc`` under ``pack``. Empty means valid.

    ``parameters`` is the manifest's parameter list, read for ``binding`` entries when
    the graph has no ``declarations`` (a 1.0/1.1 graph binds from its manifest). A graph
    with declarations binds from them and ignores ``parameters``.
    """
    if not isinstance(doc, dict):
        return [Problem("document", "/", "a graph document is a JSON object")]
    problems: list[Problem] = []
    minor = format_minor(doc)
    if minor is None:
        problems.append(Problem("version", "/version",
                                f"'version' must match 1.x (got {doc.get('version')!r})"))
        minor = 0
    if minor > FORMAT_MINOR:
        problems.append(Problem(
            "version", "/version",
            f"format 1.{minor} is newer than this core reads (1.{FORMAT_MINOR}); update the "
            f"vendored core",
        ))
    allowed = PACK_KEYS | (CORE_KEYS if minor >= 2 else frozenset())
    unknown = set(doc) - allowed
    if unknown:
        later = sorted(unknown & CORE_KEYS)
        hint = f" ({later} need format {FORMAT_VERSION})" if later else ""
        problems.append(
            Problem("document", "/", f"unknown top-level keys: {sorted(unknown)}{hint}")
        )

    kernel = doc.get("kernel", "solid" if minor < 2 else None)
    if kernel is None:
        problems.append(Problem("kernel", "/kernel",
                                f"a {FORMAT_VERSION} graph names its kernel ({list(KERNELS)})"))
    elif kernel not in KERNELS:
        problems.append(Problem("kernel", "/kernel", f"unknown kernel {kernel!r}"))
    elif kernel != pack.kernel:
        problems.append(Problem("kernel", "/kernel",
                                f"a {kernel} graph cannot be checked by the {pack.kernel} pack"))
    if not is_hashable_in(doc.get("units", "mm"), UNITS):
        problems.append(Problem("units", "/units", f"units must be one of {sorted(UNITS)}"))

    reserved = frozenset(pack.reserved_identifiers)
    catalogue = pack.catalogue()
    kinds = pack.param_kinds()
    scripts_allowed = minor >= 2 and pack.script is not None

    # ── Nodes ────────────────────────────────────────────────────────────────
    nodes = doc.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        problems.append(Problem("document", "/nodes", "'nodes' must be a non-empty array"))
        nodes = []
    elif len(nodes) > MAX_NODES:
        problems.append(
            Problem("document", "/nodes", f"too many nodes ({len(nodes)} > {MAX_NODES})")
        )
    by_id: dict[str, dict] = {}
    out_type: dict[str, str | None] = {}
    for idx, node in enumerate(nodes):
        loc = f"/nodes/{idx}"
        if not isinstance(node, dict):
            problems.append(Problem("node", loc, "must be an object"))
            continue
        extra = set(node) - NODE_KEYS
        if extra:
            problems.append(Problem("node", loc, f"unknown keys: {sorted(extra)}"))
        nid = node.get("id")
        if not isinstance(nid, str) or not IDENT_RE.match(nid) or keyword.iskeyword(nid):
            problems.append(Problem("node", loc, f"'id' must be a plain identifier (got {nid!r})"))
            continue
        if nid in by_id:
            problems.append(Problem("node", loc, f"duplicate node id '{nid}'"))
            continue
        loc = f"/nodes/{nid}"
        by_id[nid] = node
        ntype = node.get("type")
        for key in ("params", "inputs"):
            if not isinstance(node.get(key, {}), dict):
                problems.append(Problem("node", loc, f"'{key}' must be an object"))
        if ntype == SCRIPT_NODE_TYPE:
            if not scripts_allowed:
                problems.append(Problem(
                    "script-node", loc,
                    f"the script node needs format {FORMAT_VERSION} and a pack with a "
                    f"script contract",
                ))
                out_type[nid] = None
            else:
                output = as_dict(node.get("params")).get("output")
                out_type[nid] = output if isinstance(output, str) else None
            continue
        spec = catalogue.get(ntype) if isinstance(ntype, str) else None
        if spec is None:
            problems.append(Problem("node", loc, f"unknown node type {ntype!r}"))
            out_type[nid] = None
            continue
        out_type[nid] = spec.output
        params = node.get("params", {}) if isinstance(node.get("params", {}), dict) else {}
        stray = set(params) - set(spec.params)
        if stray:
            problems.append(Problem("node", loc,
                                    f"unknown params for '{ntype}': {sorted(stray)}"))
        inputs = node.get("inputs", {}) if isinstance(node.get("inputs", {}), dict) else {}
        stray = set(inputs) - set(spec.inputs)
        if stray:
            problems.append(Problem("node", loc,
                                    f"unknown input sockets for '{ntype}': {sorted(stray)}"))
        for socket, sspec in spec.inputs.items():
            if sspec.required and socket not in inputs:
                problems.append(Problem(
                    "unbound-input", f"{loc}/inputs/{socket}",
                    f"required {sspec.type} input '{socket}' is not connected",
                ))

    # ── Edges: dangling refs, socket types, fan-out ─────────────────────────────
    consumers: dict[str, list[str]] = {}
    for nid, node in by_id.items():
        spec = _spec_of(catalogue, node)
        inputs = node.get("inputs", {}) if isinstance(node.get("inputs", {}), dict) else {}
        for socket, ref in inputs.items():
            loc = f"/nodes/{nid}/inputs/{socket}"
            if not isinstance(ref, str):
                problems.append(Problem("dangling-ref", loc, "an input references a node id"))
                continue
            if ref == nid:
                problems.append(Problem("cycle", loc, "an input references the node itself"))
                continue
            if ref not in by_id:
                problems.append(Problem("dangling-ref", loc, f"references unknown node '{ref}'"))
                continue
            consumers.setdefault(ref, []).append(nid)
            if spec is not None and socket in spec.inputs:
                wanted = spec.inputs[socket].type
                got = out_type.get(ref)
                if got is not None and got != wanted:
                    problems.append(Problem(
                        "socket-type", loc, f"wants a {wanted}, but '{ref}' is a {got}"
                    ))
    for ref, users in consumers.items():
        limit = pack.fan_out.get(out_type.get(ref) or "")
        if limit is not None and len(users) > limit:
            problems.append(Problem(
                "fan-out", f"/nodes/{ref}",
                f"a {out_type[ref]} can feed {limit} node(s); '{ref}' feeds {sorted(users)}",
            ))

    # ── Cycles (Kahn) ─────────────────────────────────────────────────────────
    indegree = {nid: 0 for nid in by_id}
    for nid, node in by_id.items():
        inputs = node.get("inputs", {}) if isinstance(node.get("inputs", {}), dict) else {}
        indegree[nid] = sum(1 for r in inputs.values() if isinstance(r, str) and r in by_id
                            and r != nid)
    ready = [n for n, d in indegree.items() if d == 0]
    seen = 0
    while ready:
        current = ready.pop()
        seen += 1
        for user in consumers.get(current, []):
            indegree[user] -= 1
            if indegree[user] == 0:
                ready.append(user)
    if seen < len(by_id):
        cyclic = sorted(n for n, d in indegree.items() if d > 0)
        problems.append(Problem("cycle", "/nodes", f"dependency cycle among nodes {cyclic}"))

    # ── Outputs ───────────────────────────────────────────────────────────────
    outputs = doc.get("outputs")
    if not isinstance(outputs, dict) or not outputs:
        problems.append(Problem("document", "/outputs",
                                "'outputs' must map at least one part id to a node id"))
        outputs = {}
    elif len(outputs) > MAX_OUTPUTS:
        problems.append(Problem("document", "/outputs",
                                f"too many outputs ({len(outputs)} > {MAX_OUTPUTS})"))
    for part, ref in outputs.items():
        loc = f"/outputs/{part}"
        if not isinstance(part, str) or not part:
            problems.append(
                Problem("document", "/outputs", "output part ids are non-empty strings")
            )
        if not isinstance(ref, str) or ref not in by_id:
            problems.append(Problem("dangling-ref", loc, f"references unknown node {ref!r}"))
            continue
        got = out_type.get(ref)
        if got is not None and got not in pack.output_types:
            problems.append(Problem(
                "socket-type", loc,
                f"'{ref}' is a {got}; an output must be one of {sorted(pack.output_types)}",
            ))

    # ── Expression scope: parameters, then derived in order ────────────────────
    scope: set[str] = set()
    read: set[str] = set()
    declared = doc.get("parameters", {})
    if not isinstance(declared, dict):
        problems.append(Problem("parameters", "/parameters",
                                "'parameters' must be an object of parameter id → declaration"))
        declared = {}
    if len(declared) > MAX_PARAMETERS:
        problems.append(Problem("parameters", "/parameters",
                                f"too many parameters ({len(declared)} > {MAX_PARAMETERS})"))
    for pid, spec in declared.items():
        loc = f"/parameters/{pid}"
        bad = _identifier_problem(pid, loc, reserved)
        if bad:
            problems.append(bad)
            continue
        scope.add(pid)
        if not isinstance(spec, dict) or "default" not in spec:
            problems.append(Problem("parameters", loc, "must be an object with a 'default'"))
            continue
        if set(spec) - PARAMETER_KEYS:
            problems.append(Problem("parameters", loc,
                                    f"unknown keys: {sorted(set(spec) - PARAMETER_KEYS)}"))
        table = spec.get("map")
        if table is not None and not (
            isinstance(table, dict) and 0 < len(table) <= MAX_MAP_ENTRIES
            and all(isinstance(k, str) and OPTION_RE.match(k) for k in table)
            and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in table.values())
        ):
            problems.append(Problem(
                "parameters", f"{loc}/map",
                f"'map' is 1..{MAX_MAP_ENTRIES} plain option values → numbers",
            ))
            table = None
        default = spec["default"]
        if isinstance(default, bool) or (
            isinstance(default, (int, float)) and math.isfinite(default)
        ):
            pass
        elif isinstance(default, str) and OPTION_RE.match(default):
            if not _numeric_text(default) and default not in (table or {}):
                problems.append(Problem("parameters", loc,
                                        f"default {default!r} is neither numeric nor in 'map'"))
        else:
            problems.append(Problem("parameters", loc,
                                    "default must be a number, a boolean or an option value"))

    derived = doc.get("derived", [])
    if not isinstance(derived, list):
        problems.append(Problem("derived", "/derived", "'derived' must be an array of {id, expr}"))
        derived = []
    if len(derived) > MAX_DERIVED:
        problems.append(Problem("derived", "/derived",
                                f"too many derived values ({len(derived)} > {MAX_DERIVED})"))
    for idx, entry in enumerate(derived):
        loc = f"/derived/{idx}"
        if not isinstance(entry, dict) or set(entry) != {"id", "expr"}:
            problems.append(
                Problem("derived", loc, "must be an object with exactly 'id' and 'expr'")
            )
            continue
        bad = _identifier_problem(entry["id"], loc, reserved)
        if bad:
            problems.append(bad)
            continue
        if entry["id"] in scope:
            problems.append(Problem("derived", loc, f"'{entry['id']}' is already declared"))
            continue
        try:
            names = expression_names(parse_expression({"expr": entry["expr"]}, loc))
        except GraphCoreError as exc:
            problems.append(Problem("expression", loc, str(exc)))
        else:
            unknown_names = sorted(names - scope)
            if unknown_names:
                problems.append(Problem(
                    "expression", loc,
                    f"reads {unknown_names}, which the graph does not declare in "
                    f"'parameters' or earlier 'derived' entries",
                ))
            read |= names
        scope.add(entry["id"])

    # ── Bindings ──────────────────────────────────────────────────────────────
    has_declarations = isinstance(doc.get("declarations"), dict)
    binding_source = binding_parameters(doc, parameters)
    if has_declarations and wrapper_plan(doc, pack) is not None:
        # A pure wrapper has no node a `binding` could target. A `binding` in its
        # declarations belongs to another graph of the same cartridge (a native graph mode
        # beside the script modes), copied here because the declarations must equal the
        # manifest's entries; resolving it against the wrapper would report a dangling
        # reference that is not there (RFC 0067 P1 pre-check: book-fold-phone,
        # clamshell-dual-screen-handheld).
        binding_source = []
    try:
        bindings = extract_bindings(binding_source, reserved)
    except GraphCoreError as exc:
        problems.append(Problem("binding", "/declarations/parameters" if has_declarations
                                else "manifest:parameters", str(exc)))
        bindings = {}
    for (nid, pname), pid in bindings.items():
        loc = f"binding {pid} → {nid}.{pname}"
        node = by_id.get(nid)
        if node is None:
            problems.append(Problem("dangling-ref", loc, f"binds unknown node '{nid}'"))
            continue
        spec = _spec_of(catalogue, node)
        if spec is None:
            if node.get("type") == SCRIPT_NODE_TYPE:
                problems.append(Problem("binding", loc,
                                        "a script node is wired through its 'bind', not 'binding'"))
            continue
        if pname not in spec.params:
            problems.append(Problem(
                "dangling-ref", loc, f"node type '{node['type']}' has no param '{pname}'"
            ))
            continue
        kind = kinds.get(spec.params[pname].kind)
        if kind is not None and not kind.bindable:
            problems.append(Problem(
                "binding", loc, f"{kind.name} params cannot be bound to parameters"
            ))
        if any(True for _ in _walk_exprs(as_dict(node.get("params")).get(pname))):
            problems.append(Problem(
                "binding", loc,
                "bound to a parameter and also carries an expression; a node param takes "
                "one or the other",
            ))

    # ── Node param expressions and script nodes ─────────────────────────────────
    declared_ids = declared_parameter_ids(doc)
    passed: set[str] = set()
    script_sources: set[str] = set()
    for nid, node in by_id.items():
        loc = f"/nodes/{nid}"
        if node.get("type") == SCRIPT_NODE_TYPE:
            if not scripts_allowed:
                continue
            sp, sp_passed, sp_read = script_node_problems(
                node, loc, pack, declared_parameters=declared_ids, expression_scope=scope,
            )
            problems.extend(sp)
            passed |= sp_passed
            read |= sp_read
            source = as_dict(node.get("params")).get("source")
            if isinstance(source, str):
                script_sources.add(source)
            if "part" not in as_dict(node.get("params")) and consumers.get(nid):
                problems.append(Problem(
                    "script-node", loc,
                    "a script node without a fixed 'part' renders whichever part is "
                    f"requested, so it may feed only 'outputs', not {sorted(consumers[nid])}",
                ))
            continue
        spec = _spec_of(catalogue, node)
        if spec is None or not isinstance(node.get("params", {}), dict):
            continue
        for pname, value in node.get("params", {}).items():
            if pname not in spec.params:
                continue
            exprs = list(_walk_exprs(value))
            if not exprs:
                continue
            kind = kinds.get(spec.params[pname].kind)
            if not spec.params[pname].expr:
                problems.append(Problem(
                    "expression", f"{loc}/params/{pname}",
                    f"{kind.name if kind else spec.params[pname].kind} params take literal "
                    f"values, not expressions",
                ))
                continue
            for expr in exprs:
                try:
                    names = expression_names(parse_expression(expr, f"{loc}/params/{pname}"))
                except GraphCoreError as exc:
                    problems.append(Problem("expression", f"{loc}/params/{pname}", str(exc)))
                    continue
                unknown_names = sorted(names - scope)
                if unknown_names:
                    problems.append(Problem(
                        "expression", f"{loc}/params/{pname}",
                        f"reads {unknown_names}, which the graph does not declare in "
                        f"'parameters' or 'derived'",
                    ))
                read |= names

    script_nodes = [n for n in by_id.values() if n.get("type") == SCRIPT_NODE_TYPE]
    if scripts_allowed and script_nodes and not getattr(pack, "embedded_scripts", False) \
            and wrapper_plan(doc, pack) is None:
        problems.append(Problem(
            "script-node", "/nodes",
            f"the {pack.name} pack runs a script node only as a pure wrapper (one script "
            f"node without 'part', named by every output); a script node inside a native "
            f"graph waits for the pack to lower it (RFC 0067 P5)",
        ))

    unread = sorted(scope - read)
    if unread:
        problems.append(Problem(
            "unread-declaration", "/parameters",
            f"declared but never read by any expression: {unread}",
        ))

    # ── Format 1.2: declarations, licence, provenance ───────────────────────────
    if minor >= 2:
        if declared_ids is not None:
            stray = sorted(set(declared) - declared_ids)
            if stray:
                problems.append(Problem(
                    "declarations", "/parameters",
                    f"the expression scope reads {stray}, which 'declarations.parameters' "
                    f"does not declare",
                ))
            wired = passed | (set(declared) & read) | {pid for pid in bindings.values()}
            # The pack's part parameter (solid: `target_part`) is the runner's, not a node's:
            # it selects which output renders, and a script node passes it through by
            # contract (it may not bind it). Declared as a manifest parameter — six solid
            # cartridges do, as a part picker — it is wired by definition, and a preset may
            # set it whether or not it is declared (RFC 0067 P1 pre-check).
            part_parameters = frozenset(
                {pack.script.part_parameter} if getattr(pack, "script", None) else ()
            )
            wired = wired | (part_parameters & (declared_ids or set()))
            problems.extend(declaration_problems(doc, set(by_id), wired=wired,
                                                 part_parameters=part_parameters))
        problems.extend(provenance_problems(doc, script_sources))
    return problems


def check(doc: object, pack, *, parameters: list | None = None) -> None:
    """Raise ``GraphCoreError`` listing every problem, or return when there are none."""
    problems = validate(doc, pack, parameters=parameters)
    if problems:
        raise GraphCoreError("; ".join(str(p) for p in problems), code=problems[0].code)


def transpile(
    doc: dict,
    pack,
    *,
    parameters: list | None = None,
    source_name: str = "graph",
) -> str:
    """Validate, then have the pack transpile the document.

    A **pure wrapper** is not transpiled: the kernel renders the wrapped source through
    its own path (``wrapper_plan``), so asking for its program is an error that says so.
    A script node inside a native graph is lowered only by a pack that sets
    ``embedded_scripts``; the others refuse it here, before their transpiler sees a node
    type it does not know.
    """
    check(doc, pack, parameters=parameters)
    if wrapper_plan(doc, pack) is not None:
        raise GraphCoreError(
            f"{source_name}: a wrapper graph is rendered by invoking its source "
            f"(wrapper_plan), not transpiled",
            code="wrapper",
        )
    if any(n.get("type") == SCRIPT_NODE_TYPE for n in doc["nodes"]) and not getattr(
        pack, "embedded_scripts", False
    ):
        raise GraphCoreError(
            f"{source_name}: the {pack.name} pack does not lower a script node inside a "
            f"native graph yet (RFC 0067 P5); a wrapper graph is the supported form",
            code="script-node",
        )
    bindings = extract_bindings(binding_parameters(doc, parameters),
                                frozenset(pack.reserved_identifiers))
    return pack.transpile(pack_document(doc), bindings, source_name)
