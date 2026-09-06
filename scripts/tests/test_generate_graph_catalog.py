"""Tests for the graph node-vocabulary catalog generator.

Run standalone (there is no root pytest config; the backend suite's coverage
gate is rooted at apps/api and does not own scripts/):

    python3 -m pytest scripts/tests/test_generate_graph_catalog.py -q

``scripts/qa/generate_graph_catalog.py --check`` is a blocking step of the
``manifest-sync`` job. It exists so the studio's node editor cannot drift from
``apps/api/services/engine/graph_engine.py``, and it carries one decision that
is a security property rather than a convenience:

    bindable_kinds = {"float", "count"}

A manifest parameter may bind to a numeric node param. It may NOT bind to a
`selector`, `plane` or `axis` — those are STRUCTURAL: they are emitted into the
generated CadQuery source as literals, so a bindable one would let a
render-time request reshape the script that runs in the sandbox. The catalog is
what the studio reads to decide which sockets it may offer a binding for, so
that rule has to survive a new node type being added.

The rule is pinned twice: against a synthetic NODE_TYPES covering every kind
(so the rule is exact and does not depend on today's vocabulary), and against
the REAL graph_engine (so a new structural kind cannot be quietly added to the
bindable set). Staleness is exercised against copies in tmp_path.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "qa"))

import generate_graph_catalog as lane  # noqa: E402

sys.path.insert(0, str(REPO / "apps" / "api"))
from services.engine import graph_engine  # noqa: E402

# Kinds that carry a value into the emitted script as a literal rather than as
# a number. None of these may ever be bindable.
STRUCTURAL_KINDS = {"selector", "plane", "axis"}

SYNTHETIC_NODE_TYPES = {
    "widget": {
        "params": {
            "height": ("float", 10.0),
            "copies": ("count", 3),
            "edges": ("selector", ">Z"),
            "plane": ("plane", "XY"),
            "axis": ("axis", "Z"),
        },
        "inputs": {"shape": "solid"},
        "output": "solid",
        "emit": lambda *a, **k: "",
    },
}


@pytest.fixture
def outputs(tmp_path, monkeypatch):
    """Two committed copies of the catalog, as the repo keeps them."""
    paths = (tmp_path / "packages" / "schemas" / "graph-node-catalog.json",
             tmp_path / "apps" / "studio" / "src" / "config" / "graph-node-catalog.json")
    monkeypatch.setattr(lane, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(lane, "OUTPUT_PATHS", paths)
    return paths


@pytest.fixture
def synthetic(monkeypatch):
    monkeypatch.setattr(graph_engine, "NODE_TYPES", SYNTHETIC_NODE_TYPES)
    return lane.build_catalog()


def run(monkeypatch, *args) -> int:
    monkeypatch.setattr(sys, "argv", ["generate_graph_catalog.py", *args])
    return lane.main()


# --- the bindability rule --------------------------------------------------

def test_numeric_params_are_bindable(synthetic):
    params = synthetic["nodes"]["widget"]["params"]
    assert params["height"]["bindable"] is True
    assert params["copies"]["bindable"] is True


def test_structural_params_are_not_bindable(synthetic):
    """A render-time value must never be able to reshape the emitted script."""
    params = synthetic["nodes"]["widget"]["params"]
    for name in ("edges", "plane", "axis"):
        assert params[name]["bindable"] is False, f"{name} must stay literal"


def test_every_structural_kind_in_the_real_engine_is_unbindable():
    catalog = lane.build_catalog()
    offenders = [
        f"{node}.{param}"
        for node, spec in catalog["nodes"].items()
        for param, p in spec["params"].items()
        if p["kind"] in STRUCTURAL_KINDS and p["bindable"]
    ]
    assert offenders == []


def test_bindability_follows_the_kind_not_the_parameter_name():
    catalog = lane.build_catalog()
    by_kind: dict[str, set[bool]] = {}
    for spec in catalog["nodes"].values():
        for p in spec["params"].values():
            by_kind.setdefault(p["kind"], set()).add(p["bindable"])
    for kind, flags in by_kind.items():
        assert len(flags) == 1, f"kind {kind!r} is bindable in some nodes and not others"


# --- what the catalog carries ---------------------------------------------

def test_catalog_carries_defaults_alongside_kinds(synthetic):
    params = synthetic["nodes"]["widget"]["params"]
    assert params["height"] == {
        "kind": "float", "default": 10.0, "bindable": True, "computable": True,
    }
    assert params["plane"] == {
        "kind": "plane", "default": "XY", "bindable": False, "computable": False,
    }


def test_computability_tracks_bindability(synthetic):
    """A param an expression may compute is exactly one a parameter may bind.

    Both restrictions have the same cause — a structural value must stay
    literal so a render-time value cannot reshape the emitted script — so the
    two flags must never drift apart.
    """
    for spec in lane.build_catalog()["nodes"].values():
        for name, p in spec["params"].items():
            assert p["computable"] == p["bindable"], name


def test_catalog_carries_the_engine_limits_and_planes(synthetic):
    from services.engine import graph_expr

    assert synthetic["limits"] == {
        "max_nodes": graph_engine.MAX_NODES,
        "max_outputs": graph_engine.MAX_OUTPUTS,
        "max_pattern_count": graph_engine.MAX_PATTERN_COUNT,
        "max_expr_length": graph_expr.MAX_FORMULA_LENGTH,
        "max_expr_tokens": graph_expr.MAX_TOKENS,
    }
    assert synthetic["planes"] == sorted(graph_engine._PLANES)
    assert synthetic["graph_file_suffix"] == graph_engine.GRAPH_FILE_SUFFIX


def test_catalog_names_its_source_of_truth(synthetic):
    assert synthetic["source_of_truth"] == "apps/api/services/engine/graph_engine.py"
    assert synthetic["generated_by"] == "scripts/qa/generate_graph_catalog.py"


def test_the_emit_callable_is_never_serialised(synthetic):
    """`emit` is a function object; leaking it would make render() unserialisable."""
    assert "emit" not in synthetic["nodes"]["widget"]
    json.loads(lane.render(synthetic))  # would raise if a callable leaked in


def test_node_and_param_order_is_deterministic():
    """Two runs must byte-match, or --check flaps."""
    assert lane.render(lane.build_catalog()) == lane.render(lane.build_catalog())
    catalog = lane.build_catalog()
    assert list(catalog["nodes"]) == sorted(catalog["nodes"])
    for spec in catalog["nodes"].values():
        assert list(spec["params"]) == sorted(spec["params"])
        assert list(spec["inputs"]) == sorted(spec["inputs"])


def test_render_ends_with_a_newline(synthetic):
    assert lane.render(synthetic).endswith("}\n")


# --- the drift gate --------------------------------------------------------

def test_check_passes_when_both_copies_are_current(outputs, monkeypatch, capsys):
    text = lane.render(lane.build_catalog())
    for path in outputs:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    assert run(monkeypatch, "--check") == 0
    assert "in sync" in capsys.readouterr().out


def test_check_fails_when_only_the_studio_copy_is_stale(outputs, monkeypatch, capsys):
    _schemas, studio = outputs
    text = lane.render(lane.build_catalog())
    for path in outputs:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    studio.write_text(text.replace('"bindable": false', '"bindable": true', 1))
    assert run(monkeypatch, "--check") == 1
    out = capsys.readouterr().out
    assert "STALE" in out
    assert "graph-node-catalog.json" in out
    assert "generate_graph_catalog.py" in out  # the fix is in the message


def test_check_fails_when_a_copy_is_missing_entirely(outputs, monkeypatch):
    schemas, _ = outputs
    schemas.parent.mkdir(parents=True, exist_ok=True)
    schemas.write_text(lane.render(lane.build_catalog()))
    assert run(monkeypatch, "--check") == 1


def test_check_fails_when_a_node_type_is_added_to_the_engine(outputs, monkeypatch):
    text = lane.render(lane.build_catalog())
    for path in outputs:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    grown = dict(graph_engine.NODE_TYPES)
    grown["sprocket"] = SYNTHETIC_NODE_TYPES["widget"]
    monkeypatch.setattr(graph_engine, "NODE_TYPES", grown)
    assert run(monkeypatch, "--check") == 1


# --- the writer ------------------------------------------------------------

def test_write_mode_creates_both_copies_identically(outputs, monkeypatch):
    assert run(monkeypatch) == 0
    schemas, studio = outputs
    assert schemas.read_text() == studio.read_text()
    assert json.loads(schemas.read_text())["nodes"]


def test_write_then_check_is_clean(outputs, monkeypatch):
    assert run(monkeypatch) == 0
    assert run(monkeypatch, "--check") == 0


# --- the committed copies --------------------------------------------------

def test_the_committed_catalogs_match_the_engine():
    """The same assertion CI makes, against the real files in this repo."""
    text = lane.render(lane.build_catalog())
    for path in lane.OUTPUT_PATHS:
        assert path.is_file(), f"{path} is missing"
        assert path.read_text() == text, f"{path} is stale"
