#!/usr/bin/env python3
"""Derive CANDIDATE mating rules for the compatibility (CDG) graph — proposal only.

Yantra4D's moat is objects designed to interface with one another, but the derived
graph is nearly empty: the geometry rule table in
``apps/api/services/core/compatibility_graph.py`` admits only a handful of role
pairings, so most of the interface metadata the cartridges already declare produces
no edge at all.

This script does NOT change the graph. It reads the public cartridge manifests,
groups every declared CDG interface by ``standard family`` (the same normalization
the live graph uses) and ``role`` (the manifest's ``geometry_type``), and emits one
candidate rule per family+role-pair:

    "objects declaring standard S in role A mate with objects declaring S in role B"

For each candidate it records how many objects sit on each side, how many distinct
object pairs the rule would claim, which of those the live graph already has, whether
the live graph's geometry rule table already admits the pairing, how many pairs the
cartridge authors themselves already asserted via ``compatible_with``, and how many of
the objects are consumed across the Fashion Cabinet bridge. From those signals it
assigns a confidence tier with an explicit reason.

Nothing here is applied. Ratifying a rule is an operator decision; see
``docs/strategy/CDG-MATING-RULES-PROPOSAL.md``.

Input boundary (deliberate, and load-bearing for determinism):
  Only cartridges whose ``project.json`` lives IN THIS REPOSITORY are read — every
  ``projects/*`` path declared as a submodule in ``.gitmodules`` is skipped, whether or
  not it happens to be checked out. CI checks out submodules recursively and a
  developer usually does not; keying off "is a manifest on disk" would therefore make
  the committed artifact unreproducible, and would read private client cartridges.
  The private slugs are additionally named in ``PRIVATE_EXCLUDED`` so the guarantee
  does not rest on ``.gitmodules`` alone.

Usage:
    python3 scripts/qa/derive_mating_candidates.py            # write the artifact
    python3 scripts/qa/derive_mating_candidates.py --check    # CI drift gate
    python3 scripts/qa/derive_mating_candidates.py --refresh-bridge   # re-pin FC evidence
"""
from __future__ import annotations

import argparse
import configparser
import itertools
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
PROJECTS = REPO / "projects"
GITMODULES = REPO / ".gitmodules"
OUTPUT = REPO / "docs" / "interfaces" / "mating-candidates.json"
COMMONS_CATALOG = REPO / "docs" / "commons-catalog.json"

# The Fashion Cabinet side of the cross-commons seam. FC's bridge index lives in a
# sibling checkout that CI does not have, and an input that is present on a developer's
# machine and absent in CI would make the committed artifact unreproducible — so the only
# thing the derivation ever reads is a PINNED SNAPSHOT committed here, refreshed
# explicitly with `--refresh-bridge`. This mirrors what Fashion Cabinet already does in
# the other direction with its yantra4d-*.snapshot.json files.
BRIDGE_SNAPSHOT = REPO / "docs" / "interfaces" / "fc-bridge-consumers.snapshot.json"
BRIDGE_INDEX = REPO.parent / "fashion-cabinet" / "docs" / "interfaces" / "bridge-index.json"
BRIDGE_SNAPSHOT_SCHEMA = "fc_bridge_consumers_snapshot_v1"

SCHEMA_VERSION = "y4d_mating_candidates_v1"
GENERATOR = "scripts/qa/derive_mating_candidates.py"
PROPOSAL_DOC = "docs/strategy/CDG-MATING-RULES-PROPOSAL.md"

# Client-private cartridges. Mirrors CLIENT_PRIVATE in generate_commons_catalog.py:
# the designs are not ours to publish, so their interfaces must never reach a
# published artifact even if the submodule is checked out.
PRIVATE_EXCLUDED = ("tablaco", "tablaco-v2")

# How many worked examples to carry per rule, and the caps on evidence lists. Fixed
# constants rather than "all of them" so the artifact stays readable; every list is
# selected by a total order, so the truncation is deterministic.
MAX_EXAMPLES = 5
MAX_PARAM_HINTS = 12
MAX_UNRECOGNIZED_REPORTED = 30

TIER_ORDER = ("corroborated", "plausible", "speculative")

sys.path.insert(0, str(REPO / "apps" / "api"))

# The live graph is the single source of truth for BOTH the standard-family
# normalization and the geometry rule table. Re-stating either here would let this
# derivation drift away from the thing it is proposing changes to, so we import them.
# `_geometry_compatible` is private to that module by name only — it is the rule table
# this script exists to measure against, and a rename should break this loudly.
from services.core.compatibility_graph import (  # noqa: E402
    _geometry_compatible,
    normalize_family,
)


# ──────────────────────────────────────────────────────────────────────────────
# manifest loading
# ──────────────────────────────────────────────────────────────────────────────

def submodule_project_paths(gitmodules: Path) -> set[str]:
    """Slugs under projects/ that are git submodules — out of scope for this pass."""
    if not gitmodules.exists():
        return set()
    cp = configparser.ConfigParser()
    cp.read_string(gitmodules.read_text(encoding="utf-8"))
    out = set()
    for section in cp.sections():
        path = cp[section].get("path", "")
        if path.startswith("projects/"):
            out.add(path.split("/", 1)[1])
    return out


def _i18n(value: Any) -> str:
    """Collapse an i18n string ({en,es} or str) to English."""
    if isinstance(value, dict):
        return value.get("en") or next(iter(value.values()), "")
    return value or ""


def load_manifests(projects_dir: Path, excluded: set[str]) -> list[tuple[str, dict]]:
    """Every in-tree public cartridge manifest, as (slug, manifest), slug-sorted."""
    loaded: list[tuple[str, dict]] = []
    if not projects_dir.is_dir():
        return loaded
    for child in sorted(projects_dir.iterdir(), key=lambda p: p.name):
        if not child.is_dir() or child.name in excluded:
            continue
        manifest_path = child / "project.json"
        if not manifest_path.is_file():
            continue
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        project = data.get("project") or {}
        if project.get("unlisted"):
            continue
        loaded.append((project.get("slug") or child.name, data))
    loaded.sort(key=lambda item: item[0])
    return loaded


def _interfaces(manifest: dict) -> list[dict]:
    """The cdg_interfaces block, tolerating the legacy nesting under `project`."""
    project = manifest.get("project") or {}
    hyperobject = manifest.get("hyperobject") or project.get("hyperobject") or {}
    if not isinstance(hyperobject, dict):
        return []
    return [c for c in (hyperobject.get("cdg_interfaces") or []) if isinstance(c, dict)]


# ──────────────────────────────────────────────────────────────────────────────
# declarations
# ──────────────────────────────────────────────────────────────────────────────

def collect_declarations(manifests: list[tuple[str, dict]]) -> dict[str, Any]:
    """Flatten manifests into family-resolved role declarations plus their rejections.

    Returns declarations (one per interface that resolves to a known standard family),
    the author-declared `compatible_with` pairs between two in-scope cartridges, and a
    tally of everything that was rejected and why.
    """
    known_slugs = {slug for slug, _ in manifests}
    declarations: list[dict] = []
    declared_pairs: set[tuple[str, str]] = set()
    rejected = Counter()
    unrecognized = Counter()
    out_of_scope_links = Counter()
    interfaces_seen = 0

    for slug, manifest in manifests:
        for iface in _interfaces(manifest):
            interfaces_seen += 1
            standard = (iface.get("standard") or "").strip()
            role = (iface.get("geometry_type") or "").strip()
            family = normalize_family(standard)

            for target in iface.get("compatible_with") or []:
                if not isinstance(target, str) or target == slug:
                    continue
                if target in known_slugs:
                    declared_pairs.add(tuple(sorted((slug, target))))
                else:
                    out_of_scope_links[target] += 1

            if not role:
                rejected["no_role_declared"] += 1
                continue
            if family is None:
                lowered = standard.lower()
                if not standard or lowered in ("none", "n/a"):
                    rejected["standard_absent"] += 1
                elif lowered.startswith("internal"):
                    rejected["standard_internal"] += 1
                else:
                    rejected["standard_unrecognized"] += 1
                    unrecognized[standard] += 1
                continue

            declarations.append({
                "slug": slug,
                "family": family,
                "role": role,
                "standard": standard,
                "interface_id": iface.get("id") or "",
                "interface_label": _i18n(iface.get("label")),
                "parameters": sorted(
                    p for p in (iface.get("parameters") or []) if isinstance(p, str)
                ),
            })

    declarations.sort(key=lambda d: (d["family"], d["role"], d["slug"], d["interface_id"]))
    return {
        "declarations": declarations,
        "declared_pairs": declared_pairs,
        "rejected": rejected,
        "unrecognized": unrecognized,
        "out_of_scope_links": out_of_scope_links,
        "interfaces_seen": interfaces_seen,
    }


def baseline_graph_pairs(declarations: list[dict]) -> set[tuple[str, str]]:
    """Replay the live graph's edge derivation over exactly the in-scope declarations.

    `compatibility_graph.get_graph()` is not called directly: it walks
    `Config.CARTRIDGES_DIRS`, which varies with the environment (node_modules
    cartridges, a CARTRIDGES_DIRS override, whether submodules are checked out), and a
    committed artifact may not depend on any of that. This replays the same rule —
    same family normalization, same `_geometry_compatible` table — over the fixed,
    in-tree manifest set, so the baseline is reproducible anywhere.
    """
    by_family: dict[str, list[dict]] = defaultdict(list)
    for decl in declarations:
        by_family[decl["family"]].append(decl)

    pairs: set[tuple[str, str]] = set()
    for members in by_family.values():
        for left, right in itertools.combinations(members, 2):
            if left["slug"] == right["slug"]:
                continue
            if _geometry_compatible(left["role"], right["role"]):
                pairs.add(tuple(sorted((left["slug"], right["slug"]))))
    return pairs


def load_bridge_consumers(snapshot: Path) -> dict[str, int]:
    """Yantra4D slug -> how many Fashion Cabinet objects consume it, from the pinned snapshot.

    A missing snapshot degrades the bridge signal to zero rather than failing: the bridge
    is corroborating evidence, not a required input.
    """
    try:
        data = json.loads(snapshot.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    consumers = data.get("consumers")
    if not isinstance(consumers, dict):
        return {}
    return {
        slug: count for slug, count in sorted(consumers.items())
        if isinstance(count, int)
    }


def refresh_bridge_snapshot(bridge_index: Path, snapshot: Path) -> int:
    """Re-pin the FC bridge consumer counts from a sibling fashion-cabinet checkout."""
    try:
        data = json.loads(bridge_index.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read {bridge_index}: {exc}")
        print("Check out fashion-cabinet beside this repository and retry.")
        return 1
    targets = data.get("targets")
    if not isinstance(targets, dict) or not targets:
        print(f"ERROR: {bridge_index} carries no targets — refusing to pin an empty snapshot")
        return 1
    counts = data.get("counts") or {}
    payload = {
        "_comment": (
            "PINNED snapshot of how many Fashion Cabinet objects consume each Yantra4D "
            "cartridge, used only as corroborating evidence by " + GENERATOR + ". Do NOT "
            "hand-edit; refresh with `--refresh-bridge` beside a fashion-cabinet checkout."
        ),
        "schema_version": BRIDGE_SNAPSHOT_SCHEMA,
        "source": {
            "repo": "fashion-cabinet",
            "file": "docs/interfaces/bridge-index.json",
            "source_schema_version": data.get("schema_version", ""),
            "links": counts.get("links"),
            "targets_bridged": counts.get("targets_bridged"),
        },
        "consumers": {
            slug: len(entry.get("consumers") or [])
            for slug, entry in sorted(targets.items())
            if isinstance(entry, dict)
        },
    }
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    snapshot.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8",
    )
    print(f"Pinned {_rel(snapshot)} — {len(payload['consumers'])} bridged targets")
    return 0


# ──────────────────────────────────────────────────────────────────────────────
# candidate rules
# ──────────────────────────────────────────────────────────────────────────────

def _tier(*, two_sided: bool, author_pairs: int, rule_admits: str | None,
          role_a: str, role_b: str) -> tuple[str, str]:
    """Confidence tier for one candidate rule, with the reason that earned it.

    The ladder is about INDEPENDENT corroboration, not about plausibility to a reader:
      corroborated — two or more cartridge authors independently asserted this exact
                     pairing with `compatible_with`, and both roles have enough members
                     for the rule to be a rule rather than a single fact.
      plausible    — one corroborating signal: a single author-declared pair, or the
                     live graph's own geometry table already admitting the pairing.
      speculative  — co-declaration of one standard family and nothing else.
    """
    pairing = f"{role_a}<->{role_b}"
    if author_pairs >= 2 and two_sided:
        return "corroborated", (
            f"{author_pairs} author-declared compatible_with links already assert "
            f"{pairing} within this family, and both roles have 2+ objects"
        )
    if author_pairs >= 1 and two_sided:
        return "plausible", (
            f"1 author-declared compatible_with link asserts {pairing} within this "
            f"family; both roles have 2+ objects but a single assertion is one author"
        )
    if author_pairs >= 1:
        return "plausible", (
            f"{author_pairs} author-declared compatible_with link(s) assert {pairing}, "
            f"but one role is declared by a single object — the rule cannot be "
            f"generalised from one side"
        )
    if rule_admits and two_sided:
        return "plausible", (
            f"the live graph's geometry table already admits {pairing} (as "
            f"'{rule_admits}') and both roles have 2+ objects, but no author has "
            f"declared a pairing to confirm it"
        )
    if rule_admits:
        return "speculative", (
            f"the live graph's geometry table admits {pairing} (as '{rule_admits}'), "
            f"but one role is declared by a single object and no author declared a "
            f"pairing"
        )
    return "speculative", (
        f"co-declaration only: objects share the standard family in roles {pairing}, "
        f"with no author-declared link and no geometry rule admitting the pairing"
    )


def build_candidates(
    declarations: list[dict],
    declared_pairs: set[tuple[str, str]],
    graph_pairs: set[tuple[str, str]],
    bridge_consumers: dict[str, int],
) -> list[dict]:
    """One candidate rule per (standard family, unordered role pair) with evidence."""
    by_family: dict[str, list[dict]] = defaultdict(list)
    for decl in declarations:
        by_family[decl["family"]].append(decl)

    rules: list[dict] = []
    for family in sorted(by_family):
        members = by_family[family]
        by_role: dict[str, list[dict]] = defaultdict(list)
        for decl in members:
            by_role[decl["role"]].append(decl)
        roles = sorted(by_role)

        for role_a, role_b in itertools.combinations_with_replacement(roles, 2):
            slugs_a = {d["slug"] for d in by_role[role_a]}
            slugs_b = {d["slug"] for d in by_role[role_b]}
            object_pairs = {
                tuple(sorted((x, y)))
                for x in slugs_a for y in slugs_b
                if x != y
            }
            if not object_pairs:
                # A role pair whose only members are the same object (e.g. one
                # cartridge declaring both sides of its own joint) claims nothing.
                continue

            author_pairs = sorted(object_pairs & declared_pairs)
            in_graph = sorted(object_pairs & graph_pairs)
            rule_admits = _geometry_compatible(role_a, role_b)
            two_sided = len(slugs_a) >= 2 and len(slugs_b) >= 2
            tier, reason = _tier(
                two_sided=two_sided, author_pairs=len(author_pairs),
                rule_admits=rule_admits, role_a=role_a, role_b=role_b,
            )

            rules.append({
                "rule_id": f"{family}:{role_a}+{role_b}",
                "claim": (
                    f"objects declaring standard family '{family}' in role '{role_a}' "
                    f"mate with objects declaring it in role '{role_b}'"
                ),
                "family": family,
                "role_a": role_a,
                "role_b": role_b,
                "symmetric": role_a == role_b,
                "confidence": tier,
                "reason": reason,
                "one_sided": not two_sided,
                "members": {
                    "objects_role_a": len(slugs_a),
                    "objects_role_b": len(slugs_b),
                    "objects_total": len(slugs_a | slugs_b),
                    "objects_both_roles": len(slugs_a & slugs_b),
                },
                "claimed_pairs": len(object_pairs),
                "pairs_already_in_graph": len(in_graph),
                "new_edges": len(object_pairs) - len(in_graph),
                "evidence": {
                    "author_declared_pairs": len(author_pairs),
                    "author_declared_examples": [list(p) for p in author_pairs[:MAX_EXAMPLES]],
                    "graph_rule_admits": rule_admits,
                    "graph_agrees": bool(in_graph),
                    "bridge_objects": sum(
                        1 for s in sorted(slugs_a | slugs_b) if s in bridge_consumers
                    ),
                    "bridge_consumers": sum(
                        bridge_consumers.get(s, 0) for s in sorted(slugs_a | slugs_b)
                    ),
                    "standards_observed": sorted(
                        {d["standard"] for d in by_role[role_a] + by_role[role_b]}
                    ),
                },
                "falsification_handles": {
                    "role_a_parameters": sorted(
                        {p for d in by_role[role_a] for p in d["parameters"]}
                    )[:MAX_PARAM_HINTS],
                    "role_b_parameters": sorted(
                        {p for d in by_role[role_b] for p in d["parameters"]}
                    )[:MAX_PARAM_HINTS],
                },
                "examples": _examples(
                    by_role[role_a], by_role[role_b], declared_pairs, graph_pairs,
                ),
            })

    rules.sort(key=lambda r: (
        TIER_ORDER.index(r["confidence"]), -r["new_edges"], -r["claimed_pairs"],
        r["family"], r["role_a"], r["role_b"],
    ))
    return rules


def _examples(side_a: list[dict], side_b: list[dict],
              declared_pairs: set[tuple[str, str]],
              graph_pairs: set[tuple[str, str]]) -> list[dict]:
    """Up to MAX_EXAMPLES worked pairs, author-declared ones first, then slug order."""
    seen: set[tuple[str, str]] = set()
    rows: list[dict] = []
    for left, right in itertools.product(
        sorted(side_a, key=lambda d: (d["slug"], d["interface_id"])),
        sorted(side_b, key=lambda d: (d["slug"], d["interface_id"])),
    ):
        if left["slug"] == right["slug"]:
            continue
        key = tuple(sorted((left["slug"], right["slug"])))
        if key in seen:
            continue
        seen.add(key)
        rows.append({
            "a": left["slug"],
            "a_interface": left["interface_id"],
            "a_standard": left["standard"],
            "b": right["slug"],
            "b_interface": right["interface_id"],
            "b_standard": right["standard"],
            "author_declared": key in declared_pairs,
            "already_in_graph": key in graph_pairs,
        })
    rows.sort(key=lambda r: (not r["author_declared"], r["a"], r["b"]))
    return rows[:MAX_EXAMPLES]


# ──────────────────────────────────────────────────────────────────────────────
# projection
# ──────────────────────────────────────────────────────────────────────────────

def _density_pct(edges: int, nodes: int) -> float:
    if nodes < 2:
        return 0.0
    return round(100.0 * edges / (nodes * (nodes - 1) / 2), 4)


def project_tranches(rules: list[dict], graph_pairs: set[tuple[str, str]],
                     declarations: list[dict], declared_pairs: set[tuple[str, str]],
                     cartridges: int) -> list[dict]:
    """Cumulative graph density if each confidence tier were ratified in turn.

    Ratifying a tier is not additive in edges: two rules can claim the same object
    pair, and a claimed pair may already be an edge — so every figure is measured on
    the union of the baseline plus everything ratified up to and including that tier.

    `author_declared_pairs_explained` is the precision check on the whole exercise:
    the cartridge authors' own `compatible_with` lists are a held-out answer key the
    derivation never uses as an input to *generate* rules, only to score them. A
    tranche that adds many edges while explaining no additional author-declared pair
    is adding edges nobody has vouched for.
    """
    pairs_by_tier: dict[str, set[tuple[str, str]]] = {tier: set() for tier in TIER_ORDER}
    for rule in rules:
        pairs_by_tier[rule["confidence"]] |= _all_pairs_for_rule(rule, declarations)

    graph_nodes = sorted({d["slug"] for d in declarations})
    node_count = len(graph_nodes)
    accumulated = set(graph_pairs)
    tranches = []
    for tier in TIER_ORDER:
        added = pairs_by_tier[tier] - accumulated
        accumulated = accumulated | added
        degree = Counter()
        for left, right in accumulated:
            degree[left] += 1
            degree[right] += 1
        tranches.append({
            "tranche": tier,
            "rules": sum(1 for r in rules if r["confidence"] == tier),
            "new_edges_in_tranche": len(added),
            "edges_after": len(accumulated),
            "author_declared_pairs_explained": len(declared_pairs & accumulated),
            "author_declared_pairs_explained_pct": (
                round(100.0 * len(declared_pairs & accumulated) / len(declared_pairs), 2)
                if declared_pairs else 0.0
            ),
            "graph_nodes": node_count,
            "isolated_graph_nodes_after": sum(1 for s in graph_nodes if not degree[s]),
            "density_pct_over_graph_nodes": _density_pct(len(accumulated), node_count),
            "density_pct_over_catalog": _density_pct(len(accumulated), cartridges),
        })
    return tranches


def _all_pairs_for_rule(rule: dict, declarations: list[dict]) -> set[tuple[str, str]]:
    """Re-derive the full object-pair set a rule claims (the artifact only stores counts)."""
    slugs_a = {d["slug"] for d in declarations
               if d["family"] == rule["family"] and d["role"] == rule["role_a"]}
    slugs_b = {d["slug"] for d in declarations
               if d["family"] == rule["family"] and d["role"] == rule["role_b"]}
    return {tuple(sorted((x, y))) for x in slugs_a for y in slugs_b if x != y}


# ──────────────────────────────────────────────────────────────────────────────
# artifact
# ──────────────────────────────────────────────────────────────────────────────

def build_artifact(projects_dir: Path = PROJECTS, gitmodules: Path = GITMODULES,
                   bridge_snapshot: Path = BRIDGE_SNAPSHOT,
                   commons_catalog: Path = COMMONS_CATALOG) -> dict:
    """The whole derivation, as the dict that gets serialised to the artifact."""
    submodules = submodule_project_paths(gitmodules)
    excluded = submodules | set(PRIVATE_EXCLUDED)
    manifests = load_manifests(projects_dir, excluded)

    collected = collect_declarations(manifests)
    declarations = collected["declarations"]
    graph_pairs = baseline_graph_pairs(declarations)
    bridge_consumers = load_bridge_consumers(bridge_snapshot)
    rules = build_candidates(
        declarations, collected["declared_pairs"], graph_pairs, bridge_consumers,
    )

    graph_nodes = sorted({d["slug"] for d in declarations})
    degree = Counter()
    for left, right in graph_pairs:
        degree[left] += 1
        degree[right] += 1

    catalog_public = _catalog_size(commons_catalog)
    tier_counts = Counter(r["confidence"] for r in rules)

    return {
        "_comment": (
            "GENERATED by " + GENERATOR + " — do not hand-edit. PROPOSED, NOT APPLIED: "
            "every rule here is a candidate awaiting an operator ruling; nothing in this "
            "file changes the live compatibility graph or any cartridge manifest. See "
            + PROPOSAL_DOC + "."
        ),
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATOR,
        "status": "proposed",
        "inputs": {
            "cartridges_scanned": len(manifests),
            "cartridges_public_total": catalog_public,
            "cartridges_out_of_scope_submodules": (
                None if catalog_public is None else catalog_public - len(manifests)
            ),
            "scope_note": (
                "in-tree projects/*/project.json only; every projects/* submodule path "
                "declared in .gitmodules is skipped whether or not it is checked out, so "
                "the artifact is identical with and without `--recurse-submodules` and no "
                "client-private cartridge is ever read"
            ),
            "interfaces_declared": collected["interfaces_seen"],
            "interfaces_with_resolved_family": len(declarations),
            "objects_with_resolved_family": len(graph_nodes),
            "author_declared_pairs_in_scope": len(collected["declared_pairs"]),
            "author_declared_links_out_of_scope": sum(
                collected["out_of_scope_links"].values()
            ),
            "bridge_snapshot_available": bool(bridge_consumers),
            "bridge_targets": len(bridge_consumers),
        },
        "graph_baseline": {
            "note": (
                "the live graph's own rule replayed over the in-scope manifests; see "
                "baseline_graph_pairs() for why get_graph() is not called directly"
            ),
            "graph_nodes": len(graph_nodes),
            "edges": len(graph_pairs),
            "isolated_graph_nodes": sum(1 for s in graph_nodes if not degree[s]),
            "density_pct_over_graph_nodes": _density_pct(len(graph_pairs), len(graph_nodes)),
            "density_pct_over_catalog": _density_pct(len(graph_pairs), len(manifests)),
            "author_declared_pairs_reproduced": len(collected["declared_pairs"] & graph_pairs),
            "author_declared_pairs_missing": len(collected["declared_pairs"] - graph_pairs),
            "author_declared_pairs_without_shared_family": len(
                collected["declared_pairs"] - _same_family_pairs(declarations)
            ),
        },
        "tier_summary": {tier: tier_counts.get(tier, 0) for tier in TIER_ORDER},
        "projection": project_tranches(
            rules, graph_pairs, declarations, collected["declared_pairs"],
            len(manifests),
        ),
        "rejected_interfaces": {
            "counts": dict(sorted(collected["rejected"].items())),
            "unrecognized_standards": [
                {"standard": standard, "interfaces": count}
                for standard, count in sorted(
                    collected["unrecognized"].items(), key=lambda kv: (-kv[1], kv[0])
                )[:MAX_UNRECOGNIZED_REPORTED]
            ],
            "unrecognized_standards_distinct": len(collected["unrecognized"]),
        },
        "rules": rules,
    }


def _same_family_pairs(declarations: list[dict]) -> set[tuple[str, str]]:
    """Every object pair that shares at least one resolved standard family.

    The outer bound on what ANY family+role rule can ever claim. Author-declared pairs
    outside it are unreachable by this derivation at all: they need a normalization fix
    to `normalize_family`, or a different edge source entirely.
    """
    by_family: dict[str, set[str]] = defaultdict(set)
    for decl in declarations:
        by_family[decl["family"]].add(decl["slug"])
    pairs: set[tuple[str, str]] = set()
    for slugs in by_family.values():
        for left, right in itertools.combinations(sorted(slugs), 2):
            pairs.add((left, right))
    return pairs


def _catalog_size(commons_catalog: Path) -> int | None:
    """How many public cartridges the committed Commons catalog knows about."""
    try:
        data = json.loads(commons_catalog.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    counts = data.get("counts") or {}
    value = counts.get("cartridges")
    return value if isinstance(value, int) else None


def _rel(path: Path) -> str:
    """Repo-relative path for messages, tolerating a path outside the repo (tests)."""
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return str(path)


def serialize(artifact: dict) -> str:
    return json.dumps(artifact, indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Derive candidate CDG mating rules (proposal only; applies nothing)",
    )
    parser.add_argument("--check", action="store_true",
                        help="fail if the committed artifact differs from a fresh derivation")
    parser.add_argument("--refresh-bridge", action="store_true",
                        help="re-pin the Fashion Cabinet bridge snapshot from a sibling checkout")
    args = parser.parse_args()

    if args.refresh_bridge:
        return refresh_bridge_snapshot(BRIDGE_INDEX, BRIDGE_SNAPSHOT)

    artifact = build_artifact()
    if not artifact["rules"]:
        print("ERROR: no candidate rules derived — refusing to write an empty artifact")
        return 1
    payload = serialize(artifact)

    if args.check:
        if not OUTPUT.exists():
            print(f"ERROR: {_rel(OUTPUT)} is missing")
            print(f"Regenerate with: python3 {GENERATOR}")
            return 1
        if OUTPUT.read_text(encoding="utf-8") != payload:
            print(f"ERROR: {_rel(OUTPUT)} is stale")
            print(f"Regenerate with: python3 {GENERATOR}")
            return 1
        print(f"Mating candidates up to date ({len(artifact['rules'])} candidate rules)")
        return 0

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(payload, encoding="utf-8")
    summary = ", ".join(
        f"{tier} {count}" for tier, count in artifact["tier_summary"].items()
    )
    print(f"Wrote {_rel(OUTPUT)} — {len(artifact['rules'])} candidate rules ({summary})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
