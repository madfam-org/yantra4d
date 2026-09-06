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
from typing import ClassVar
from unittest.mock import patch

import pytest

from services.engine.graph_engine import (
    NODE_TYPES,
    GraphError,
    extract_bindings,
    load_graph_document,
    parameter_defaults,
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


def solid_graph(nodes, out="o"):
    return {"version": "1.0.0", "nodes": nodes, "outputs": {"part": out}}


class TestProfilesAndExtrude:
    def test_profile_rect_extrude(self):
        script = transpile(solid_graph([
            {"id": "p", "type": "profile_rect", "params": {"w": 40, "d": 20}},
            {"id": "o", "type": "extrude", "inputs": {"profile": "p"}, "params": {"height": 8}},
        ]))
        assert '_n_p = cq.Workplane("XY").center(0.0, 0.0).rect(40.0, 20.0)' in script
        assert "_n_o = _n_p.extrude(8.0)" in script

    def test_profile_plane_and_offset(self):
        script = transpile(solid_graph([
            {"id": "p", "type": "profile_circle",
             "params": {"r": 6, "x": 12, "y": -3, "plane": "XZ"}},
            {"id": "o", "type": "extrude", "inputs": {"profile": "p"}, "params": {"height": 4}},
        ]))
        assert '_n_p = cq.Workplane("XZ").center(12.0, -3.0).circle(6.0)' in script

    def test_polygon_sides_is_a_count(self):
        script = transpile(solid_graph([
            {"id": "p", "type": "profile_polygon", "params": {"sides": 8, "diameter": 30}},
            {"id": "o", "type": "extrude", "inputs": {"profile": "p"}, "params": {"height": 3}},
        ]))
        assert ".polygon(8, 30.0)" in script

    def test_extrude_rejects_a_solid_input(self):
        with pytest.raises(GraphError, match="wants a profile"):
            transpile(solid_graph([
                {"id": "b", "type": "box", "params": {}},
                {"id": "o", "type": "extrude", "inputs": {"profile": "b"}, "params": {}},
            ]))

    def test_boolean_rejects_a_profile_input(self):
        with pytest.raises(GraphError, match="wants a solid"):
            transpile(solid_graph([
                {"id": "p", "type": "profile_rect", "params": {}},
                {"id": "b", "type": "box", "params": {}},
                {"id": "o", "type": "union", "inputs": {"a": "b", "b": "p"}},
            ]))

    def test_profile_cannot_be_an_output(self):
        with pytest.raises(GraphError, match="extrude it into a solid"):
            transpile({
                "version": "1.0.0",
                "nodes": [{"id": "p", "type": "profile_rect", "params": {}}],
                "outputs": {"part": "p"},
            })

    @pytest.mark.parametrize("plane", ["xy", "ZZ", "", 4])
    def test_bad_plane(self, plane):
        with pytest.raises(GraphError, match="plane"):
            transpile(solid_graph([
                {"id": "p", "type": "profile_rect", "params": {"plane": plane}},
                {"id": "o", "type": "extrude", "inputs": {"profile": "p"}, "params": {}},
            ]))


class TestSolidOperations:
    def test_shell_hollows_with_negative_thickness(self):
        script = transpile(solid_graph([
            {"id": "b", "type": "box", "params": {}},
            {"id": "o", "type": "shell", "inputs": {"shape": "b"},
             "params": {"thickness": 2, "face": ">Z"}},
        ]))
        assert '_n_o = _n_b.faces(">Z").shell(-2.0)' in script

    def test_hole(self):
        script = transpile(solid_graph([
            {"id": "b", "type": "box", "params": {}},
            {"id": "o", "type": "hole", "inputs": {"shape": "b"}, "params": {"diameter": 6}},
        ]))
        assert '_n_o = _n_b.faces(">Z").workplane().hole(6.0)' in script

    def test_mirror_unions_with_source(self):
        script = transpile(solid_graph([
            {"id": "b", "type": "box", "params": {}},
            {"id": "o", "type": "mirror", "inputs": {"shape": "b"}, "params": {"plane": "YZ"}},
        ]))
        assert '_n_o = _n_b.union(_n_b.mirror("YZ"))' in script


class TestPatterns:
    def _pattern(self, ptype, params):
        return transpile(solid_graph([
            {"id": "b", "type": "box", "params": {}},
            {"id": "o", "type": ptype, "inputs": {"shape": "b"}, "params": params},
        ]))

    def test_linear_pattern_emits_bounded_loop(self):
        script = self._pattern("pattern_linear", {"count": 4, "dx": 15})
        assert "for _i_n_o in range(1, 4):" in script
        assert "_n_b.translate((15.0 * _i_n_o, 0.0 * _i_n_o, 0.0 * _i_n_o))" in script
        compile(script, "<generated>", "exec")

    def test_polar_pattern_emits_bounded_loop(self):
        script = self._pattern("pattern_polar", {"count": 6, "angle": 60})
        assert "for _i_n_o in range(1, 6):" in script
        assert "rotate((0, 0, 0), (0, 0, 1), 60.0 * _i_n_o)" in script
        compile(script, "<generated>", "exec")

    @pytest.mark.parametrize("count", [0, -3, 201, 2.5, True, "4"])
    def test_count_out_of_range_or_wrong_type(self, count):
        with pytest.raises(GraphError):
            self._pattern("pattern_linear", {"count": count})

    def test_bound_count_is_clamped_in_generated_code(self):
        bindings = extract_bindings([{"id": "copies", "binding": "o.count"}])
        script = transpile(solid_graph([
            {"id": "b", "type": "box", "params": {}},
            {"id": "o", "type": "pattern_linear", "inputs": {"shape": "b"},
             "params": {"count": 3}},
        ]), bindings)
        # A slider wired to a pattern count must not be able to detonate the worker.
        assert "min(max(int(_param(lambda: copies, 3)), 1), 200)" in script
        compile(script, "<generated>", "exec")

    @pytest.mark.parametrize("kind_param", ["plane", "face"])
    def test_structural_params_are_not_bindable(self, kind_param):
        node = ({"id": "o", "type": "profile_rect", "params": {}} if kind_param == "plane"
                else {"id": "o", "type": "shell", "inputs": {"shape": "b"}, "params": {}})
        nodes = [{"id": "b", "type": "box", "params": {}}]
        nodes.append(node)
        if kind_param == "plane":
            nodes.append({"id": "e", "type": "extrude", "inputs": {"profile": "o"}, "params": {}})
            out = "e"
        else:
            out = "o"
        bindings = extract_bindings([{"id": "p", "binding": f"o.{kind_param}"}])
        with pytest.raises(GraphError, match="cannot be bound"):
            transpile(solid_graph(nodes, out), bindings)


@pytest.mark.skipif(not HAS_CADQUERY, reason="cadquery not installed")
class TestVocabularyRendersRealGeometry:
    """Every node type must produce real geometry, not just valid Python."""

    CASES: ClassVar[dict] = {
        "extrude_rect": [
            {"id": "p", "type": "profile_rect", "params": {"w": 40, "d": 20}},
            {"id": "o", "type": "extrude", "inputs": {"profile": "p"}, "params": {"height": 8}},
        ],
        "extrude_polygon": [
            {"id": "p", "type": "profile_polygon", "params": {"sides": 6, "diameter": 24}},
            {"id": "o", "type": "extrude", "inputs": {"profile": "p"}, "params": {"height": 5}},
        ],
        "shell": [
            {"id": "b", "type": "box", "params": {"w": 40, "d": 30, "h": 20}},
            {"id": "o", "type": "shell", "inputs": {"shape": "b"}, "params": {"thickness": 2}},
        ],
        "hole": [
            {"id": "b", "type": "box", "params": {"w": 40, "d": 30, "h": 10}},
            {"id": "o", "type": "hole", "inputs": {"shape": "b"}, "params": {"diameter": 8}},
        ],
        "pattern_polar": [
            {"id": "b", "type": "box", "params": {"w": 8, "d": 8, "h": 4}},
            {"id": "t", "type": "translate", "inputs": {"shape": "b"}, "params": {"x": 25}},
            {"id": "o", "type": "pattern_polar", "inputs": {"shape": "t"},
             "params": {"count": 6, "angle": 60}},
        ],
    }

    @pytest.mark.parametrize("case", sorted(CASES))
    def test_renders_stl(self, case, tmp_path):
        script = transpile(solid_graph(self.CASES[case]), {}, case)
        script_path = tmp_path / f"{case}.py"
        script_path.write_text(script)
        runner = Path(__file__).resolve().parents[2] / "services" / "engine" / "cq_runner.py"
        out_path = tmp_path / f"{case}.stl"
        result = subprocess.run(
            [sys.executable, str(runner), str(script_path), str(out_path),
             json.dumps({"target_part": "part"}), "stl"],
            capture_output=True, text=True, timeout=180, check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert out_path.stat().st_size > 500


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

    @pytest.mark.skipif(not HAS_CADQUERY, reason="cadquery not installed")
    def test_an_expression_is_recomputed_per_render_not_frozen(self, tmp_path):
        """The property the whole design turns on.

        `prepare_graph_script` runs once per graph+manifest and caches the
        script; per-request values arrive later as globals `_param` reads. So
        an expression folded to a constant at transpile time would be *inert* —
        the slider would move and the geometry would not. ONE script, rendered
        twice with different values, must give two different solids.
        """
        import trimesh

        graph_path = tmp_path / "live.graph.json"
        graph_path.write_text(json.dumps({
            "version": "1.1.0",
            "nodes": [{"id": "b", "type": "box",
                       "params": {"w": {"expr": "n * 10"}, "d": 5, "h": 5}}],
            "outputs": {"p": "b"},
        }))
        manifest = SimpleNamespace(parameters=[{"id": "n", "default": 1.0}])
        script_path = prepare_graph_script(str(graph_path), manifest)

        runner = Path(__file__).resolve().parents[2] / "services" / "engine" / "cq_runner.py"
        widths = {}
        for n in (1, 3):
            out_path = tmp_path / f"n{n}.stl"
            result = subprocess.run(
                [sys.executable, str(runner), script_path, str(out_path),
                 json.dumps({"target_part": "p", "n": n}), "stl"],
                capture_output=True, text=True, timeout=120, check=False,
            )
            assert result.returncode == 0, result.stdout + result.stderr
            widths[n] = trimesh.load(str(out_path)).extents[0]

        assert widths[1] == pytest.approx(10.0, abs=0.01)
        assert widths[3] == pytest.approx(30.0, abs=0.01)


class TestExpressionAndParameterInputs:
    """`{"expr": "..."}` and `{"param": id}` param values (lane G-EXPR).

    The property that matters: an expression is *parsed* at transpile time —
    unknown identifiers and syntax errors are hard errors there — but *emitted*
    as arithmetic over the same `_param` probes a binding uses, so a derived
    dimension stays live at render time instead of freezing into a constant.
    """

    def _graph(self, params, node_type="box"):
        """One node of `node_type`, fed a box when the type needs a shape."""
        node = {"id": "b", "type": node_type, "params": params}
        if NODE_TYPES[node_type]["inputs"]:
            node["inputs"] = {"shape": "src"}
            return {
                "version": "1.1.0",
                "nodes": [{"id": "src", "type": "box"}, node],
                "outputs": {"p": "b"},
            }
        return {
            "version": "1.1.0",
            "nodes": [node],
            "outputs": {"p": "b"},
        }

    def _transpile(self, params, parameters=None, node_type="box"):
        return transpile(
            self._graph(params, node_type), {}, "t.graph.json", parameters or {}
        )

    # ── emission ──────────────────────────────────────────────────────────────

    def test_expression_emits_live_probe_arithmetic(self):
        script = self._transpile({"w": {"expr": "width / 2"}}, {"width": 60.0})
        assert "_param(lambda: width, 60.0)" in script
        assert "_expr_div" in script
        # ...and the value is NOT frozen to the default.
        assert "30.0" not in script

    def test_parameter_reference_emits_the_same_probe_as_a_binding(self):
        script = self._transpile({"w": {"param": "width"}}, {"width": 60.0})
        assert "float(_param(lambda: width, 60.0))" in script

    def test_a_literal_expression_folds_to_a_number(self):
        script = self._transpile({"w": {"expr": "2 + 3 * 4"}})
        assert "cq.Workplane(\"XY\").box(14.0," in script
        # No live parameter, so no runtime helpers are emitted at all.
        assert "_expr_num" not in script
        assert "import math" not in script

    def test_the_runtime_preamble_appears_only_when_needed(self):
        plain = transpile(make_graph())
        assert "_expr_num" not in plain
        assert "import math" not in plain
        live = self._transpile({"w": {"expr": "width * 2"}}, {"width": 3.0})
        assert "def _expr_num(value):" in live
        assert "import math" in live

    def test_a_graph_without_expressions_is_byte_identical_to_before(self):
        # The whole point of the conditional preamble: adding expressions to the
        # engine must not rewrite the script of any existing graph cartridge.
        assert transpile(make_graph()) == transpile(make_graph(), {}, "graph", {})

    def test_a_computed_count_is_rounded_and_clamped(self):
        script = self._transpile(
            {"count": {"expr": "n * 2"}, "angle": 30.0},
            {"n": 3},
            node_type="pattern_polar",
        )
        assert "min(max(int(round(" in script
        assert ", 1), 200)" in script

    def test_the_emitted_script_is_syntactically_valid_python(self):
        script = self._transpile(
            {"w": {"expr": "a > 2 ? a * 2 : a / 2"}, "d": {"expr": "!a ? 1 : a % 3"}},
            {"a": 5.0},
        )
        compile(script, "<graph>", "exec")

    # ── validation ────────────────────────────────────────────────────────────

    def test_unknown_identifier_is_a_hard_error(self):
        with pytest.raises(GraphError, match="unknown parameter"):
            self._transpile({"w": {"expr": "nope * 2"}}, {"width": 1.0})

    def test_every_unknown_identifier_is_named_at_once(self):
        with pytest.raises(GraphError, match=r"\['one', 'two'\]"):
            self._transpile({"w": {"expr": "one + two"}}, {})

    def test_a_syntax_error_is_a_hard_error_not_a_silent_literal(self):
        with pytest.raises(GraphError, match="invalid expression"):
            self._transpile({"w": {"expr": "(1 + 2"}})

    @pytest.mark.parametrize(
        "expr",
        [
            'constructor.constructor("return process")()',
            "a.b",
            'a["b"]',
            "a = 1",
            "1, 2",
            "() => 1",
            "`x`",
            "__import__",
            "1 # 2",
        ],
    )
    def test_escapes_are_refused(self, expr):
        with pytest.raises(GraphError):
            self._transpile({"w": {"expr": expr}}, {"a": 1.0})

    def test_an_over_long_expression_is_refused(self):
        with pytest.raises(GraphError, match="too long"):
            self._transpile({"w": {"expr": "1 +" * 200 + "1"}})

    def test_an_over_token_expression_is_refused(self):
        with pytest.raises(GraphError, match="too many tokens"):
            self._transpile({"w": {"expr": "1+" * 80 + "1"}})

    def test_a_structural_param_cannot_be_an_expression(self):
        with pytest.raises(GraphError, match="must stay a literal"):
            transpile(
                {
                    "version": "1.1.0",
                    "nodes": [
                        {"id": "b", "type": "box"},
                        {
                            "id": "c",
                            "type": "chamfer",
                            "inputs": {"shape": "b"},
                            "params": {"edges": {"expr": "1"}},
                        },
                    ],
                    "outputs": {"p": "c"},
                },
                {},
                "t.graph.json",
                {},
            )

    def test_a_structural_param_cannot_reference_a_parameter(self):
        with pytest.raises(GraphError, match="must stay a literal"):
            transpile(
                {
                    "version": "1.1.0",
                    "nodes": [
                        {"id": "b", "type": "box"},
                        {
                            "id": "r",
                            "type": "rotate",
                            "inputs": {"shape": "b"},
                            "params": {"axis": {"param": "a"}},
                        },
                    ],
                    "outputs": {"p": "r"},
                },
                {},
                "t.graph.json",
                {"a": 1.0},
            )

    @pytest.mark.parametrize(
        "value",
        [{}, {"param": "a", "expr": "a"}, {"nope": 1}, {"expr": "a", "other": 2}],
    )
    def test_a_param_object_needs_exactly_one_known_key(self, value):
        with pytest.raises(GraphError):
            self._transpile({"w": value}, {"a": 1.0})

    def test_expr_must_be_a_string(self):
        with pytest.raises(GraphError, match="'expr' must be a string"):
            self._transpile({"w": {"expr": 42}})

    def test_a_reference_to_an_undeclared_parameter_is_refused(self):
        with pytest.raises(GraphError, match="unknown parameter 'nope'"):
            self._transpile({"w": {"param": "nope"}}, {"width": 1.0})

    def test_a_reference_to_a_reserved_name_is_refused(self):
        with pytest.raises(GraphError, match="reserved name"):
            self._transpile({"w": {"param": "result"}}, {"result": 1.0})

    def test_an_expression_naming_a_reserved_identifier_is_refused(self):
        with pytest.raises(GraphError, match="unknown parameter"):
            self._transpile({"w": {"expr": "result * 2"}}, {"result": 1.0})

    def test_a_graph_expression_and_a_manifest_binding_cannot_both_drive_a_param(self):
        with pytest.raises(GraphError, match="use one or the other"):
            transpile(
                self._graph({"w": {"expr": "width * 2"}}),
                {("b", "w"): "width"},
                "t.graph.json",
                {"width": 3.0},
            )

    def test_a_folded_expression_is_range_checked_like_a_literal(self):
        # 0 is out of the count range; the fold must not sneak past _literal.
        with pytest.raises(GraphError, match="count must be between"):
            self._transpile(
                {"count": {"expr": "1 - 1"}, "angle": 30.0}, {}, node_type="pattern_polar"
            )

    def test_a_folded_fractional_count_is_refused(self):
        with pytest.raises(GraphError, match="must be whole"):
            self._transpile(
                {"count": {"expr": "3 / 2"}, "angle": 30.0}, {}, node_type="pattern_polar"
            )

    def test_a_folded_boolean_is_not_a_number(self):
        with pytest.raises(GraphError, match="boolean, not a number"):
            self._transpile({"w": {"expr": "1 > 0"}})

    def test_a_parameter_without_a_numeric_default_is_unknown(self):
        # parameter_defaults drops non-numeric defaults, so naming one is the
        # same error as naming something that does not exist.
        params = parameter_defaults([{"id": "style", "default": "wide"}])
        assert params == {}
        with pytest.raises(GraphError, match="unknown parameter"):
            self._transpile({"w": {"expr": "style * 2"}}, params)


class TestParameterDefaults:
    def test_collects_numeric_and_boolean_defaults(self):
        assert parameter_defaults(
            [
                {"id": "a", "default": 1},
                {"id": "b", "default": 2.5},
                {"id": "flag", "default": True},
            ]
        ) == {"a": 1, "b": 2.5, "flag": True}

    @pytest.mark.parametrize(
        "entry",
        [
            {"id": "s", "default": "wide"},
            {"id": "n", "default": None},
            {"id": "l", "default": [1]},
            {"id": "", "default": 1},
            {"id": "9bad", "default": 1},
            {"id": "class", "default": 1},
            {"id": "_hidden", "default": 1},
            {"id": "result", "default": 1},
            {"id": "no_default"},
        ],
    )
    def test_drops_what_an_expression_cannot_use(self, entry):
        assert parameter_defaults([entry]) == {}

    def test_tolerates_junk_entries(self):
        assert parameter_defaults([None, "x", 5, {"id": "ok", "default": 1}]) == {"ok": 1}

    def test_none_is_empty(self):
        assert parameter_defaults(None) == {}
