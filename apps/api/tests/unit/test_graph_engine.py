"""
Unit tests for the graph engine (graph.json → CadQuery transpiler).

The transpiler is a security boundary: every substituted value must be a
validated literal or a `_param` probe — never raw text from the document.
These tests lock that property, the deterministic emission, and the
engine-registration seams (manifest inference, orchestrator gating).
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from services.engine.graph_engine import (
    GraphError,
    extract_bindings,
    load_graph_document,
    prepare_graph_script,
    transpile,
)

HAS_CADQUERY = importlib.util.find_spec("cadquery") is not None


def make_graph(**overrides):
    """A small valid graph: filleted plate with one hole."""
    doc = {
        "version": "1.0.0",
        "nodes": [
            {"id": "base", "type": "box", "params": {"w": 60, "d": 40, "h": 8}},
            {"id": "hole", "type": "cylinder", "params": {"r": 3.2, "h": 20}},
            {
                "id": "hole_pos",
                "type": "translate",
                "inputs": {"shape": "hole"},
                "params": {"x": -20, "y": 0, "z": 0},
            },
            {"id": "body", "type": "cut", "inputs": {"a": "base", "b": "hole_pos"}},
            {
                "id": "soft",
                "type": "fillet",
                "inputs": {"shape": "body"},
                "params": {"edges": "|Z", "radius": 2},
            },
        ],
        "outputs": {"bracket": "soft"},
    }
    doc.update(overrides)
    return doc


class TestTranspileEmission:
    def test_golden_lines(self):
        script = transpile(make_graph())
        assert '_n_base = cq.Workplane("XY").box(60.0, 40.0, 8.0)' in script
        assert '_n_hole = cq.Workplane("XY").cylinder(20.0, 3.2)' in script
        assert "_n_hole_pos = _n_hole.translate((-20.0, 0.0, 0.0))" in script
        assert "_n_body = _n_base.cut(_n_hole_pos)" in script
        assert '_n_soft = _n_body.edges("|Z").fillet(2.0)' in script
        assert '"bracket": _n_soft,' in script
        assert '_target = str(_param(lambda: target_part, "bracket"))' in script

    def test_generated_script_is_valid_python(self):
        script = transpile(make_graph())
        compile(script, "<generated>", "exec")

    def test_deterministic(self):
        assert transpile(make_graph()) == transpile(make_graph())

    def test_out_of_order_nodes_emit_topologically(self):
        doc = {
            "version": "1.0",
            "nodes": [
                {"id": "joined", "type": "union", "inputs": {"a": "one", "b": "two"}},
                {"id": "one", "type": "box", "params": {}},
                {"id": "two", "type": "sphere", "params": {"r": 4}},
            ],
            "outputs": {"part": "joined"},
        }
        script = transpile(doc)
        assert script.index("_n_one = ") < script.index("_n_joined = ")
        assert script.index("_n_two = ") < script.index("_n_joined = ")
        compile(script, "<generated>", "exec")

    def test_empty_selector_means_all_edges(self):
        doc = {
            "version": "1.0",
            "nodes": [
                {"id": "b", "type": "box", "params": {}},
                {"id": "c", "type": "chamfer", "inputs": {"shape": "b"}, "params": {"distance": 1}},
            ],
            "outputs": {"p": "c"},
        }
        script = transpile(doc)
        assert "_n_c = _n_b.edges().chamfer(1.0)" in script

    def test_rotate_axis_maps_to_unit_vector(self):
        doc = {
            "version": "1.0",
            "nodes": [
                {"id": "b", "type": "box", "params": {}},
                {
                    "id": "r",
                    "type": "rotate",
                    "inputs": {"shape": "b"},
                    "params": {"axis": "y", "angle": 30},
                },
            ],
            "outputs": {"p": "r"},
        }
        script = transpile(doc)
        assert "_n_r = _n_b.rotate((0, 0, 0), (0, 1, 0), 30.0)" in script

    def test_part_id_with_quote_is_escaped(self):
        doc = make_graph(outputs={'he"llo': "soft"})
        script = transpile(doc)
        assert '"he\\"llo": _n_soft,' in script
        compile(script, "<generated>", "exec")


class TestValidationRejects:
    @pytest.mark.parametrize("version", [None, 7, "2.0.0", "0.1.0", "1x"])
    def test_bad_version(self, version):
        with pytest.raises(GraphError, match="version"):
            transpile(make_graph(version=version))

    def test_non_mm_units(self):
        with pytest.raises(GraphError, match="units"):
            transpile(make_graph(units="in"))

    def test_unknown_top_level_key(self):
        with pytest.raises(GraphError, match="unknown top-level"):
            transpile(make_graph(edges=[]))

    def test_unknown_node_type(self):
        doc = make_graph(nodes=[{"id": "a", "type": "loft"}], outputs={"p": "a"})
        with pytest.raises(GraphError, match="unknown node type"):
            transpile(doc)

    def test_unknown_param_name(self):
        doc = make_graph(
            nodes=[{"id": "a", "type": "box", "params": {"width": 5}}], outputs={"p": "a"}
        )
        with pytest.raises(GraphError, match="unknown params"):
            transpile(doc)

    @pytest.mark.parametrize("bad_id", ["1abc", "a-b", "for", "", "_hidden", "a b"])
    def test_bad_node_id(self, bad_id):
        doc = make_graph(nodes=[{"id": bad_id, "type": "box"}], outputs={"p": bad_id})
        with pytest.raises(GraphError, match="identifier"):
            transpile(doc)

    def test_duplicate_node_id(self):
        doc = make_graph(
            nodes=[{"id": "a", "type": "box"}, {"id": "a", "type": "sphere"}],
            outputs={"p": "a"},
        )
        with pytest.raises(GraphError, match="duplicate"):
            transpile(doc)

    def test_missing_required_input(self):
        doc = make_graph(nodes=[{"id": "a", "type": "box"}, {"id": "u", "type": "union", "inputs": {"a": "a"}}], outputs={"p": "u"})
        with pytest.raises(GraphError, match="requires inputs"):
            transpile(doc)

    def test_dangling_input_reference(self):
        doc = make_graph(
            nodes=[
                {"id": "a", "type": "box"},
                {"id": "t", "type": "translate", "inputs": {"shape": "ghost"}},
            ],
            outputs={"p": "t"},
        )
        with pytest.raises(GraphError, match="unknown node 'ghost'"):
            transpile(doc)

    def test_self_reference(self):
        doc = make_graph(
            nodes=[{"id": "t", "type": "translate", "inputs": {"shape": "t"}}],
            outputs={"p": "t"},
        )
        with pytest.raises(GraphError, match="references the node itself"):
            transpile(doc)

    def test_cycle(self):
        doc = make_graph(
            nodes=[
                {"id": "a", "type": "translate", "inputs": {"shape": "b"}},
                {"id": "b", "type": "translate", "inputs": {"shape": "a"}},
            ],
            outputs={"p": "a"},
        )
        with pytest.raises(GraphError, match="cycle"):
            transpile(doc)

    def test_output_referencing_unknown_node(self):
        with pytest.raises(GraphError, match="output"):
            transpile(make_graph(outputs={"p": "nope"}))

    @pytest.mark.parametrize("value", [float("nan"), float("inf"), True, "12", None])
    def test_bad_float_values(self, value):
        doc = make_graph(nodes=[{"id": "a", "type": "box", "params": {"w": value}}], outputs={"p": "a"})
        with pytest.raises(GraphError):
            transpile(doc)

    @pytest.mark.parametrize(
        "selector",
        ['"); import os  # ', "|Z'", 'a"b', "x" * 121],
    )
    def test_selector_injection_blocked(self, selector):
        doc = make_graph(
            nodes=[
                {"id": "b", "type": "box"},
                {
                    "id": "f",
                    "type": "fillet",
                    "inputs": {"shape": "b"},
                    "params": {"edges": selector, "radius": 1},
                },
            ],
            outputs={"p": "f"},
        )
        with pytest.raises(GraphError, match="selector"):
            transpile(doc)

    def test_bad_axis(self):
        doc = make_graph(
            nodes=[
                {"id": "b", "type": "box"},
                {"id": "r", "type": "rotate", "inputs": {"shape": "b"}, "params": {"axis": "w"}},
            ],
            outputs={"p": "r"},
        )
        with pytest.raises(GraphError, match="axis"):
            transpile(doc)

    def test_too_many_nodes(self):
        nodes = [{"id": f"n{i}", "type": "box"} for i in range(501)]
        with pytest.raises(GraphError, match="too many nodes"):
            transpile(make_graph(nodes=nodes, outputs={"p": "n0"}))

    def test_unknown_node_key(self):
        doc = make_graph(nodes=[{"id": "a", "type": "box", "position": [0, 0]}], outputs={"p": "a"})
        with pytest.raises(GraphError, match="unknown keys"):
            transpile(doc)


class TestBindings:
    def _params(self, **binding_by_id):
        return [{"id": pid, "binding": b} for pid, b in binding_by_id.items()]

    def test_bound_param_reads_manifest_value(self):
        bindings = extract_bindings(self._params(width="base.w"))
        script = transpile(make_graph(), bindings)
        assert "float(_param(lambda: width, 60.0))" in script
        compile(script, "<generated>", "exec")

    def test_unbound_params_stay_literal(self):
        bindings = extract_bindings(self._params(width="base.w"))
        script = transpile(make_graph(), bindings)
        assert "40.0" in script  # base.d remains a literal

    def test_binding_unknown_node(self):
        bindings = extract_bindings(self._params(width="ghost.w"))
        with pytest.raises(GraphError, match="unknown node"):
            transpile(make_graph(), bindings)

    def test_binding_unknown_param(self):
        bindings = extract_bindings(self._params(width="base.radius"))
        with pytest.raises(GraphError, match="no param"):
            transpile(make_graph(), bindings)

    def test_binding_selector_rejected(self):
        bindings = extract_bindings(self._params(sel="soft.edges"))
        with pytest.raises(GraphError, match="selector"):
            transpile(make_graph(), bindings)

    @pytest.mark.parametrize("pid", ["target_part", "cq", "_x", "for", "result"])
    def test_reserved_or_invalid_parameter_ids(self, pid):
        with pytest.raises(GraphError):
            extract_bindings([{"id": pid, "binding": "base.w"}])

    def test_malformed_binding_string(self):
        with pytest.raises(GraphError, match="invalid binding"):
            extract_bindings([{"id": "width", "binding": "base-w"}])

    def test_duplicate_binding_target(self):
        with pytest.raises(GraphError, match="more than one"):
            extract_bindings(self._params(a="base.w", b="base.w"))

    def test_parameters_without_binding_are_ignored(self):
        assert extract_bindings([{"id": "plain"}, {"id": "s", "type": "slider"}]) == {}

    def test_list_binding_drives_multiple_node_params(self):
        bindings = extract_bindings([{"id": "size", "binding": ["base.w", "base.d"]}])
        assert bindings == {("base", "w"): "size", ("base", "d"): "size"}
        script = transpile(make_graph(), bindings)
        assert "float(_param(lambda: size, 60.0))" in script
        assert "float(_param(lambda: size, 40.0))" in script

    def test_list_binding_with_non_string_entry(self):
        with pytest.raises(GraphError, match="invalid binding"):
            extract_bindings([{"id": "size", "binding": ["base.w", 7]}])


class TestLoadAndPrepare:
    def _write_graph(self, tmp_path, doc, name="model.graph.json"):
        path = tmp_path / name
        path.write_text(json.dumps(doc))
        return path

    def test_load_rejects_wrong_suffix(self, tmp_path):
        path = tmp_path / "model.json"
        path.write_text("{}")
        with pytest.raises(GraphError, match="graph file must end"):
            load_graph_document(str(path))

    def test_load_rejects_oversized(self, tmp_path):
        path = self._write_graph(tmp_path, {})
        path.write_text("x" * (256 * 1024 + 1))
        with pytest.raises(GraphError, match="exceeds"):
            load_graph_document(str(path))

    def test_load_rejects_invalid_json(self, tmp_path):
        path = tmp_path / "model.graph.json"
        path.write_text("{nope")
        with pytest.raises(GraphError, match="not valid JSON"):
            load_graph_document(str(path))

    def test_prepare_is_idempotent_and_content_addressed(self, tmp_path):
        path = self._write_graph(tmp_path, make_graph())
        manifest = SimpleNamespace(parameters=[])
        first = prepare_graph_script(str(path), manifest)
        second = prepare_graph_script(str(path), manifest)
        assert first == second
        assert first.endswith(".py")
        assert Path(first).is_file()

    def test_prepare_keys_on_bindings(self, tmp_path):
        path = self._write_graph(tmp_path, make_graph())
        plain = prepare_graph_script(str(path), SimpleNamespace(parameters=[]))
        bound = prepare_graph_script(
            str(path),
            SimpleNamespace(parameters=[{"id": "width", "binding": "base.w"}]),
        )
        assert plain != bound
        assert "float(_param(lambda: width, 60.0))" in Path(bound).read_text()


class TestManifestIntegration:
    def _manifest(self, mode):
        from manifest import ProjectManifest
        data = {
            "project": {"slug": "t", "engine": "openscad"},
            "modes": [mode],
            "parts": [],
            "parameters": [],
        }
        return ProjectManifest(data, Path("/tmp"))

    def test_graph_engine_inferred_from_extension(self):
        m = self._manifest({"id": "m", "scad_file": "model.graph.json", "parts": ["p"]})
        assert m.mode_engine("m") == "graph"

    def test_explicit_graph_engine_on_mode(self):
        m = self._manifest({"id": "m", "scad_file": "model.graph.json", "engine": "graph", "parts": ["p"]})
        assert m.mode_engine("m") == "graph"

    def test_project_level_graph_engine_accepted(self):
        from manifest import ProjectManifest
        data = {"project": {"slug": "t", "engine": "graph"}, "modes": [], "parts": [], "parameters": []}
        assert ProjectManifest(data, Path("/tmp")).engine == "graph"


class TestOrchestratorGating:
    def _resolve(self, tier, export_format):
        from services.engine.render_orchestrator import resolve_engine_config
        manifest = SimpleNamespace(mode_engine=lambda mode_id: "graph", modes=[])
        payload = {
            "project_slug": "t",
            "export_format": export_format,
            "scad_path": "/proj/model.graph.json",
        }
        with patch("services.engine.render_orchestrator.get_manifest", return_value=manifest):
            return resolve_engine_config({"mode": "m"}, payload, tier)

    def test_pro_tier_step_allowed(self):
        engine, _path, actual, err = self._resolve("pro", "step")
        assert engine == "graph"
        assert actual == "step"
        assert err is None

    def test_guest_tier_forbidden(self):
        engine, _path, actual, err = self._resolve("guest", "stl")
        assert engine == "graph"
        assert actual is None
        assert err is not None
        assert err[1] == 403

    def test_unsupported_format_rejected(self):
        _, _, actual, err = self._resolve("pro", "off")
        assert actual is None
        assert err is not None
        assert err[1] == 400


@pytest.mark.skipif(not HAS_CADQUERY, reason="cadquery not installed")
class TestEndToEndExecution:
    def test_generated_script_renders_stl_via_cq_runner(self, tmp_path):
        graph_path = tmp_path / "model.graph.json"
        graph_path.write_text(json.dumps(make_graph()))
        manifest = SimpleNamespace(parameters=[{"id": "width", "binding": "base.w"}])
        script_path = prepare_graph_script(str(graph_path), manifest)

        runner = Path(__file__).resolve().parents[2] / "services" / "engine" / "cq_runner.py"
        out_path = tmp_path / "out.stl"
        params = json.dumps({"target_part": "bracket", "width": 80})
        result = subprocess.run(
            [sys.executable, str(runner), script_path, str(out_path), params, "stl"],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert out_path.is_file()
        assert out_path.stat().st_size > 100
