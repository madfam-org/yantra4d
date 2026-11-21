"""What a graph declares to the world: parameters, groups, presets, constraints, interfaces.

RFC 0067 §2: a hyperobject has a configurable graph when every parameter a visitor can
set, every preset, every constraint and every CDG interface is declared **by the graph**,
and the manifest's lists are generated from it rather than kept by hand. Format 1.2 puts
them in one top-level block::

    "declarations": {
      "parameters":       [ ...manifest parameter objects... ],
      "parameter_groups": [ ... ],
      "presets":          [ ... ],
      "constraints":      [ ... ],
      "interfaces":       [ ...CDG interfaces... ]
    }

Each entry has exactly the shape the commons' manifest already gives it, so the
projection back to a manifest is a copy (``manifest_projection``) and a manifest that
drifted from its graph is a plain inequality. The core checks only what the graph's
meaning depends on — identities, references, wiring and the constraint dialect — and
leaves value ranges and widget details to the manifest's own checker, so a declaration
copied from a conformant manifest is never refused here for a reason the manifest
checker would not give.

Labels are i18n strings (a plain string, or ``{"en": ..., "es": ..., "fr": ..., "pt":
...}`` with ``en`` required, RFC 0039). ``label_keys`` gives every surface string in a
graph a stable key, so a generated configurator and a completeness check address the
same strings the same way in all three commons.
"""

from __future__ import annotations

import copy

from .errors import GraphCoreError, Problem, as_list, is_hashable_in
from .expression import expression_names, parse_expression
from .script_node import IDENT_RE

DECLARATION_KEYS = ("parameters", "parameter_groups", "presets", "constraints", "interfaces")
PARAMETER_TYPES = frozenset({"slider", "checkbox", "select", "text"})
SEVERITIES = frozenset({"error", "warning"})
#: RFC 0039: the commons is quadrilingual. ``en`` is the one a label must carry.
LOCALES = ("en", "es", "fr", "pt")

__all__ = [
    "DECLARATION_KEYS",
    "LOCALES",
    "PARAMETER_TYPES",
    "declaration_problems",
    "declared_bindings",
    "declared_parameter_ids",
    "i18n_gaps",
    "label_keys",
    "manifest_projection",
]


def _i18n_ok(value: object) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    return (
        isinstance(value, dict)
        and isinstance(value.get("en"), str)
        and bool(value["en"].strip())
        and all(isinstance(v, str) for v in value.values())
    )


def _entry_id(entry: dict, keys: tuple[str, ...]) -> object:
    for key in keys:
        if key in entry:
            return entry[key]
    return None


def declared_parameter_ids(doc: dict) -> set[str] | None:
    """The declared parameter ids, or None when the graph has no declarations block."""
    block = doc.get("declarations")
    if not isinstance(block, dict):
        return None
    return {
        p["id"] for p in as_list(block.get("parameters"))
        if isinstance(p, dict) and isinstance(p.get("id"), str)
    }


def declared_bindings(doc: dict) -> list[dict]:
    """The ``parameters`` list a binding map is read from: the declarations when the
    graph has them, else nothing (the caller supplies the manifest's)."""
    block = doc.get("declarations")
    if isinstance(block, dict) and isinstance(block.get("parameters"), list):
        return [p for p in block["parameters"] if isinstance(p, dict)]
    return []


def declaration_problems(
    doc: dict,
    node_ids: set[str],
    *,
    wired: set[str],
) -> list[Problem]:
    """Check the declarations block. ``wired`` is every declared parameter id that some
    node reads: a script pass-through, a ``binding``, or the graph's expression scope."""
    block = doc.get("declarations")
    if block is None:
        return []
    where = "/declarations"
    if not isinstance(block, dict):
        return [Problem("declarations", where, "must be an object")]
    problems: list[Problem] = []
    unknown = set(block) - set(DECLARATION_KEYS)
    if unknown:
        problems.append(Problem("declarations", where, f"unknown keys: {sorted(unknown)}"))
    for key in DECLARATION_KEYS:
        if key in block and not isinstance(block[key], list):
            problems.append(Problem("declarations", f"{where}/{key}", "must be an array"))
            return problems

    # Groups first: parameters name them.
    groups: set[str] = set()
    for idx, group in enumerate(as_list(block.get("parameter_groups"))):
        loc = f"{where}/parameter_groups/{idx}"
        gid = _entry_id(group, ("id", "key", "slug")) if isinstance(group, dict) else None
        if not isinstance(gid, str) or not gid:
            problems.append(Problem("declarations", loc, "a group needs an id, key or slug"))
            continue
        if gid in groups:
            problems.append(Problem("declarations", loc, f"duplicate group {gid!r}"))
        groups.add(gid)
        if not _i18n_ok(group.get("label")):
            problems.append(Problem("i18n", loc, "a group needs a label (an 'en' string)"))

    params: dict[str, dict] = {}
    declared_ids = {
        p["id"] for p in as_list(block.get("parameters"))
        if isinstance(p, dict) and isinstance(p.get("id"), str)
    }
    for idx, param in enumerate(as_list(block.get("parameters"))):
        loc = f"{where}/parameters/{idx}"
        if not isinstance(param, dict):
            problems.append(Problem("declarations", loc, "must be an object"))
            continue
        pid = param.get("id")
        if not isinstance(pid, str) or not IDENT_RE.match(pid):
            problems.append(Problem("declarations", loc, f"id {pid!r} is not a plain identifier"))
            continue
        loc = f"{where}/parameters/{pid}"
        if pid in params:
            problems.append(Problem("declarations", loc, "duplicate parameter id"))
        params[pid] = param
        if not is_hashable_in(param.get("type"), PARAMETER_TYPES):
            problems.append(Problem(
                "declarations", loc,
                f"type {param.get('type')!r} is not one of {sorted(PARAMETER_TYPES)}",
            ))
        if "default" not in param:
            problems.append(Problem("declarations", loc, "needs a 'default'"))
        if not _i18n_ok(param.get("label")):
            problems.append(Problem("i18n", loc, "needs a label (an 'en' string)"))
        visible = param.get("visible_when")
        if visible is not None:
            # A surface shows or hides this control by a 1.1 expression over the
            # declared parameters (the generated configurator reads it).
            try:
                tree = parse_expression(visible, f"{loc}/visible_when")
            except GraphCoreError as exc:
                problems.append(Problem("expression", f"{loc}/visible_when", str(exc)))
            else:
                late = sorted(expression_names(tree) - declared_ids)
                if late:
                    problems.append(Problem(
                        "expression", f"{loc}/visible_when",
                        f"reads {late}, which are not declared parameters",
                    ))
        group = param.get("group")
        if group is not None and groups and not is_hashable_in(group, groups):
            problems.append(Problem(
                "declarations", loc, f"group {group!r} is not a declared parameter group"
            ))
        unused = param.get("intentionally_unused")
        allow_unused = isinstance(unused, dict) and isinstance(unused.get("reason"), str) \
            and bool(unused["reason"].strip())
        if unused is not None and not allow_unused:
            problems.append(Problem(
                "dead-parameter", loc, "'intentionally_unused' needs a non-empty 'reason'"
            ))
        if pid not in wired and not allow_unused:
            problems.append(Problem(
                "dead-parameter", loc,
                "no node reads this parameter: pass it through a script binding, bind it "
                "('binding'), read it in an expression, or allow-list it with a reason",
            ))

    presets: set[str] = set()
    for idx, preset in enumerate(as_list(block.get("presets"))):
        loc = f"{where}/presets/{idx}"
        if not isinstance(preset, dict):
            problems.append(Problem("declarations", loc, "must be an object"))
            continue
        pid = _entry_id(preset, ("id", "slug"))
        if isinstance(pid, str) and pid:
            if pid in presets:
                problems.append(Problem("declarations", loc, f"duplicate preset {pid!r}"))
            presets.add(pid)
        if not _i18n_ok(preset.get("label")):
            problems.append(Problem("i18n", loc, "a preset needs a label (an 'en' string)"))
        values = preset.get("values")
        if not isinstance(values, dict):
            problems.append(Problem("declarations", loc, "'values' must be an object"))
            continue
        stray = sorted(set(values) - set(params))
        if stray:
            problems.append(Problem(
                "declarations", loc,
                f"sets {stray}, which are not declared parameters",
            ))

    for idx, constraint in enumerate(as_list(block.get("constraints"))):
        loc = f"{where}/constraints/{idx}"
        if not isinstance(constraint, dict):
            problems.append(Problem("declarations", loc, "must be an object"))
            continue
        source = constraint.get("expression", constraint.get("rule"))
        if source is not None:
            try:
                tree = parse_expression(source, loc)
            except GraphCoreError as exc:
                problems.append(Problem("expression", loc, str(exc)))
            else:
                undeclared = sorted(expression_names(tree) - set(params))
                if undeclared:
                    problems.append(Problem(
                        "expression", loc,
                        f"reads {undeclared}, which are not declared parameters",
                    ))
        if "message" in constraint and not _i18n_ok(constraint["message"]):
            problems.append(Problem("i18n", loc, "the message needs an 'en' string"))
        if not is_hashable_in(constraint.get("severity", "warning"), SEVERITIES):
            problems.append(Problem(
                "declarations", loc, f"severity must be one of {sorted(SEVERITIES)}"
            ))

    interfaces: set[str] = set()
    for idx, iface in enumerate(as_list(block.get("interfaces"))):
        loc = f"{where}/interfaces/{idx}"
        if not isinstance(iface, dict) or not isinstance(iface.get("id"), str):
            problems.append(Problem("declarations", loc, "an interface needs an 'id'"))
            continue
        iid = iface["id"]
        if iid in interfaces:
            problems.append(Problem("declarations", loc, f"duplicate interface {iid!r}"))
        interfaces.add(iid)
        if not _i18n_ok(iface.get("label")):
            problems.append(Problem("i18n", loc, "an interface needs a label (an 'en' string)"))
        stray = sorted(
            str(x) for x in as_list(iface.get("parameters")) if not is_hashable_in(x, params)
        )
        if stray:
            problems.append(Problem(
                "declarations", loc, f"names {stray}, which are not declared parameters"
            ))
        node = iface.get("node")
        if node is not None and not is_hashable_in(node, node_ids):
            problems.append(Problem(
                "dangling-ref", loc, f"node {node!r} is not a node of this graph"
            ))
    return problems


def manifest_projection(doc: dict) -> dict:
    """The manifest lists this graph generates: a deep copy of each declared list.

    Only the lists the graph declares appear. Where a kernel's manifest keeps a list
    elsewhere (solid: ``hyperobject.cdg_interfaces``), the kernel's adapter places it.
    """
    block = doc.get("declarations")
    if not isinstance(block, dict):
        return {}
    return {
        key: copy.deepcopy(block[key]) for key in DECLARATION_KEYS
        if isinstance(block.get(key), list)
    }


def _label_pairs(prefix: str, entry: dict, fields: tuple[str, ...]):
    for field in fields:
        if field in entry:
            yield f"{prefix}.{field}", entry[field]


def label_keys(doc: dict) -> dict[str, object]:
    """Every surface string a graph declares, under a stable key.

    Keys: ``parameters.<id>.label|tooltip``, ``parameters.<id>.options.<value>.label``,
    ``parameter_groups.<id>.label``, ``presets.<id>.label``,
    ``constraints.<index>.message``, ``interfaces.<id>.label``, ``nodes.<id>.label``
    (a node's ``meta.label``). The value is the i18n string as declared.
    """
    out: dict[str, object] = {}
    block = doc.get("declarations") if isinstance(doc.get("declarations"), dict) else {}
    for param in as_list(block.get("parameters")):
        if not isinstance(param, dict) or not isinstance(param.get("id"), str):
            continue
        prefix = f"parameters.{param['id']}"
        out.update(_label_pairs(prefix, param, ("label", "tooltip")))
        for option in as_list(param.get("options")):
            if isinstance(option, dict) and "value" in option and "label" in option:
                out[f"{prefix}.options.{option['value']}.label"] = option["label"]
    for group in as_list(block.get("parameter_groups")):
        if isinstance(group, dict):
            gid = _entry_id(group, ("id", "key", "slug"))
            if isinstance(gid, str):
                out.update(_label_pairs(f"parameter_groups.{gid}", group, ("label",)))
    for preset in as_list(block.get("presets")):
        if isinstance(preset, dict):
            pid = _entry_id(preset, ("id", "slug"))
            if isinstance(pid, str):
                out.update(_label_pairs(f"presets.{pid}", preset, ("label",)))
    for idx, constraint in enumerate(as_list(block.get("constraints"))):
        if isinstance(constraint, dict):
            out.update(_label_pairs(f"constraints.{idx}", constraint, ("message",)))
    for iface in as_list(block.get("interfaces")):
        if isinstance(iface, dict) and isinstance(iface.get("id"), str):
            out.update(_label_pairs(f"interfaces.{iface['id']}", iface, ("label",)))
    for node in as_list(doc.get("nodes")):
        meta = node.get("meta") if isinstance(node, dict) else None
        if isinstance(meta, dict) and "label" in meta and isinstance(node.get("id"), str):
            out[f"nodes.{node['id']}.label"] = meta["label"]
    return out


def i18n_gaps(doc: dict, locales: tuple[str, ...] = LOCALES) -> list[tuple[str, str]]:
    """``(key, locale)`` for every surface string missing a locale.

    A plain-string label counts as ``en`` only. A report, never a refusal: the surface
    checks of RFC 0067 §5 decide what a gap costs.
    """
    gaps = []
    for key, value in sorted(label_keys(doc).items()):
        present = {"en"} if isinstance(value, str) else {
            k for k, v in value.items() if isinstance(v, str) and v.strip()
        } if isinstance(value, dict) else set()
        gaps.extend((key, loc) for loc in locales if loc not in present)
    return gaps
