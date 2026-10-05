"""
Wave D of the graph engine: expressions (G-EXPR), `select`, `reflect`,
`profile_polyline` (G-NODES-1) and the bounded `revolve` (G-NODES-2).

The expression evaluator must agree with apps/studio/src/lib/safeFormula.ts,
which the Studio uses to evaluate the same formulas live. The SEMANTICS table
below pins the cases where JavaScript and Python differ by default (strict
equality, truncating remainder, eager && / || and ?:, NaN truthiness, numeric
strings); every expected value in it was produced by safeFormula.ts itself.

The security property of the transpiler is unchanged and is pinned again here:
an expression's text never reaches the generated script — only validated float
literals, declared variable reads and a fixed set of helper calls do.
"""
import importlib.util
import json
import math
import re
import subprocess
import sys
from pathlib import Path
from typing import ClassVar

import pytest

from services.engine import graph_engine
from services.engine.graph_engine import GraphError, transpile

HAS_CADQUERY = importlib.util.find_spec("cadquery") is not None
RUNNER = Path(__file__).resolve().parents[2] / "services" / "engine" / "cq_runner.py"
SCHEMA = Path(__file__).resolve().parents[4] / "packages" / "schemas" / "graph.schema.json"


def evaluate(source: str, env: dict):
    """Compile `source` the way transpile() does and run it with the runtime helpers."""
    namespace: dict = {}
    exec(graph_engine._EXPR_HELPERS, namespace)  # noqa: S102 - the engine's own helper text
    scope = graph_engine._ExprScope()
    for name, value in env.items():
        scope.variables[name] = f"_g_p_{name}"
        namespace[f"_g_p_{name}"] = namespace["_g_in"](value, None, name, None)
    return eval(scope.compile({"expr": source}, "test"), namespace)


def expr_graph(nodes, parameters=None, derived=None, outputs=None):
    doc = {"version": "1.1.0", "nodes": nodes, "outputs": outputs or {"part": nodes[-1]["id"]}}
    if parameters is not None:
        doc["parameters"] = parameters
    if derived is not None:
        doc["derived"] = derived
    return doc


def box(node_id="b", **params):
    return {"id": node_id, "type": "box", "params": params or {"w": 10, "d": 10, "h": 10}}


ENV = {"a": 7.5, "b": "608", "c": True, "d": 0, "e": -3, "f": False}


class TestExpressionSemantics:
    # (formula, expected) — expected values come from evaluateSafeFormula(formula, ENV).
    SEMANTICS: ClassVar[list] = [
        ("a + 1", 8.5),
        ("-a % 3", -1.5),          # truncating remainder, not Python's floor modulo
        ("a % -2", 1.5),
        ("e % 2", -1.0),
        ("1 + 2 * 3 % 4", 3.0),
        ("10 % 3 % 2", 1.0),
        ("b == 608", True),         # a numeric string reads as a number
        ("c == 1", False),          # == is strict: a boolean never equals a number
        ("c != 1", True),
        ("c + c", 2.0),             # arithmetic coerces like Number()
        ("c > f", True),
        ("d ? 1 : 2", 2.0),
        ("c && a", True),           # && / || return booleans, not operands
        ("d || f", False),
        ("1 < 2 < 3", True),        # (1 < 2) < 3 -> true < 3 -> 1 < 3
        ("3 > 2 > 1", False),
        ("a > 1 ? e > 0 ? 1 : 2 : 3", 2.0),
        ("d == -0", True),
        (".5 + 1.", 1.5),
        ("!d", True),
        ("-(-(a))", 7.5),
    ]

    @pytest.mark.parametrize(("source", "expected"), SEMANTICS)
    def test_matches_safe_formula(self, source, expected):
        value = evaluate(source, ENV)
        assert type(value) is type(expected)
        assert value == expected

    @pytest.mark.parametrize("source", [
        "1 / 0", "a % 0", "1 || 1 / 0", "0 && 1 / 0", "c ? 1 : 1 / 0",
    ])
    def test_both_sides_are_evaluated_like_the_studio(self, source):
        # safeFormula evaluates both operands of && / || and both ?: branches, so a
        # division by zero anywhere is an error there; it must be one here too.
        with pytest.raises(ZeroDivisionError):
            evaluate(source, ENV)

    def test_nan_is_falsy(self):
        # inf - inf is NaN; JavaScript treats NaN as false, Python's bool() would not.
        assert evaluate("big * big - big * big ? 1 : 2", {"big": 1e300}) == 2.0


class TestExpressionSyntax:
    @pytest.mark.parametrize(("source", "message"), [
        ("a +", "expected value"),
        ("(a", "expected closing parenthesis"),
        ("a ? 1", "expected conditional separator"),
        ("a)", "unexpected trailing token"),
        ("a ? 1 : 2 : 3", "unexpected trailing token"),
        ("a = 1", "unsupported token"),
        ("'1'", "unsupported token"),
        ("a.b", "unsupported token"),
        ("__import__('os')", "unsupported token"),
        ("max(a, 1)", "unsupported token"),
        ("1" * 257, "too long"),
        ("+".join(["1"] * 65), "too many tokens"),
    ])
    def test_rejected(self, source, message):
        with pytest.raises(GraphError, match=message):
            evaluate(source, ENV)

    def test_unknown_identifier_is_named(self):
        with pytest.raises(GraphError, match=r"reads \['width'\]"):
            evaluate("width / 2", ENV)

    def test_dollar_identifiers_tokenize_but_never_resolve(self):
        # safeFormula's identifiers allow `$`; no declared name can contain it.
        with pytest.raises(GraphError, match="does not declare"):
            evaluate("$a + 1", ENV)

    def test_deep_nesting_is_refused_before_exec(self):
        with pytest.raises(GraphError, match="nests too deeply"):
            evaluate("!" * 120 + "a", ENV)


class TestParameterReads:
    def run(self, value, table=None, default=None):
        namespace: dict = {}
        exec(graph_engine._EXPR_HELPERS, namespace)  # noqa: S102
        return namespace["_g_in"](value, default, "p", table)

    def test_numbers_and_booleans_pass_through(self):
        assert self.run(3) == 3.0
        assert isinstance(self.run(3), float)
        assert self.run(True) is True

    def test_numeric_strings_parse(self):
        assert self.run("608") == 608.0
        assert self.run(" 2.5 ") == 2.5

    def test_missing_value_uses_default(self):
        assert self.run(None, default=30.0) == 30.0

    def test_map_turns_option_names_into_numbers(self):
        assert self.run("NEMA23", table={"NEMA17": 17.0, "NEMA23": 23.0}) == 23.0

    @pytest.mark.parametrize("value", ["NEMA17", "1_0", "0x10", "inf", "", [1]])
    def test_non_numeric_values_fail_loudly(self, value):
        with pytest.raises(ValueError, match="not numeric"):
            self.run(value)


class TestDeclarations:
    NODE: ClassVar[dict] = {"id": "b", "type": "box", "params": {"w": {"expr": "width"}}}

    def test_parameters_and_derived_emit_reads_in_order(self):
        doc = expr_graph(
            [{"id": "b", "type": "box", "params": {"w": {"expr": "half * 2"}}}],
            parameters={"width": {"default": 40}},
            derived=[{"id": "half", "expr": "width / 2"}],
        )
        script = transpile(doc, {}, "t")
        assert '_g_p_width = _g_in(_param(lambda: width, None), 40.0, "width", None)' in script
        assert "_g_d_half = _g_div(_g_p_width, 2.0)" in script
        assert script.index("_g_p_width =") < script.index("_g_d_half =") < script.index("_n_b =")
        assert '_g_float((float(_g_d_half) * float(2.0)), "b.w")' in script

    def test_map_is_emitted_as_a_literal_table(self):
        doc = expr_graph(
            [{"id": "b", "type": "box", "params": {"w": {"expr": "nema"}}}],
            parameters={"nema": {"default": "NEMA17", "map": {"NEMA17": 42.3, "NEMA23": 57}}},
        )
        assert '{"NEMA17": 42.3, "NEMA23": 57.0}' in transpile(doc, {}, "t")

    @pytest.mark.parametrize(("parameters", "derived", "message"), [
        ({"width": {"default": 1}, "spare": {"default": 2}}, None, r"never read.*'spare'"),
        ({"width": {"default": 1}}, [{"id": "unused", "expr": "1"}], r"never read.*'unused'"),
        ({"width": {}}, None, "must be an object with a 'default'"),
        ({"width": {"default": 1, "min": 0}}, None, "unknown keys"),
        ({"width": {"default": "NEMA17"}}, None, "neither numeric nor in 'map'"),
        ({"width": {"default": "a'b"}}, None, "number, a boolean or an option value"),
        ({"width": {"default": 1, "map": {"a'b": 1}}}, None, "not a plain option value"),
        ({"width": {"default": 1, "map": {}}}, None, "'map' must be an object"),
        ({"cq": {"default": 1}}, None, "reserved"),
        ({"_x": {"default": 1}}, None, "not a plain identifier"),
        ({"width": {"default": math.inf}}, None, "finite"),
        ({"width": {"default": 1}}, [{"id": "width", "expr": "1"}], "already declared"),
        ({"width": {"default": 1}}, [{"id": "h", "expr": "later"}, {"id": "later", "expr": "width"}],
         "does not declare"),
        ({"width": {"default": 1}}, [{"id": "h"}], "exactly 'id' and 'expr'"),
    ])
    def test_rejected(self, parameters, derived, message):
        doc = expr_graph([self.NODE], parameters=parameters, derived=derived)
        with pytest.raises(GraphError, match=message):
            transpile(doc, {}, "t")

    def test_expression_on_a_structural_param_is_refused(self):
        node = {"id": "b", "type": "fillet", "inputs": {"shape": "x"},
                "params": {"edges": {"expr": "1"}}}
        with pytest.raises(GraphError, match="selector params take literal values"):
            transpile(expr_graph([box("x"), node]), {}, "t")

    def test_binding_and_expression_on_one_param_conflict(self):
        doc = expr_graph([self.NODE], parameters={"width": {"default": 1}})
        with pytest.raises(GraphError, match="one or the other"):
            transpile(doc, {("b", "w"): "width"}, "t")

    def test_expression_must_be_a_single_expr_object(self):
        node = {"id": "b", "type": "box", "params": {"w": {"expr": "1", "note": "x"}}}
        with pytest.raises(GraphError, match="one key, 'expr'"):
            transpile(expr_graph([node]), {}, "t")

    def test_count_expressions_are_clamped_in_the_script(self):
        node = {"id": "p", "type": "pattern_linear", "inputs": {"shape": "b"},
                "params": {"count": {"expr": "(n - n % 20) / 20"}}}
        doc = expr_graph([box(), node], parameters={"n": {"default": 45}})
        assert "_g_count(" in transpile(doc, {}, "t")
        namespace: dict = {}
        exec(graph_engine._EXPR_HELPERS, namespace)  # noqa: S102
        assert namespace["_g_count"](10_000.0, "x") == graph_engine.MAX_PATTERN_COUNT
        assert namespace["_g_count"](-4.0, "x") == 1

    def test_version_1_0_graphs_transpile_without_helpers(self):
        script = transpile(expr_graph([box()]), {}, "t")
        assert "_g_" not in script
        assert "import math" not in script

    def test_expression_text_never_reaches_the_script(self):
        doc = expr_graph(
            [{"id": "b", "type": "box", "params": {"w": {"expr": "width   *   2"}}}],
            parameters={"width": {"default": 3}},
        )
        script = transpile(doc, {}, "t")
        assert "width   *   2" not in script
        # Every identifier in the emitted node line is engine-owned.
        line = next(ln for ln in script.splitlines() if ln.startswith("_n_b ="))
        names = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", re.sub(r'"[^"]*"', '""', line)))
        assert names <= {"_n_b", "cq", "Workplane", "box", "_g_float", "float", "_g_p_width"}


class TestNewNodes:
    def test_reflect_is_a_pure_mirror(self):
        node = {"id": "r", "type": "reflect", "inputs": {"shape": "b"}, "params": {"plane": "YZ"}}
        assert '_n_r = _n_b.mirror("YZ")' in transpile(expr_graph([box(), node]), {}, "t")

    def test_select_emits_a_conditional_choice(self):
        nodes = [box("a"), box("b"), {"id": "s", "type": "select",
                                      "inputs": {"if_true": "a", "if_false": "b"},
                                      "params": {"when": {"expr": "on"}}}]
        script = transpile(expr_graph(nodes, parameters={"on": {"default": False}}), {}, "t")
        assert "_n_s = _n_a if _g_truth(_g_p_on) else _n_b" in script

    def test_select_literal_condition_must_be_boolean(self):
        nodes = [box("a"), box("b"), {"id": "s", "type": "select",
                                      "inputs": {"if_true": "a", "if_false": "b"},
                                      "params": {"when": 1}}]
        with pytest.raises(GraphError, match="true or false"):
            transpile(expr_graph(nodes), {}, "t")

    def test_select_condition_cannot_be_bound(self):
        nodes = [box("a"), box("b"), {"id": "s", "type": "select",
                                      "inputs": {"if_true": "a", "if_false": "b"}}]
        with pytest.raises(GraphError, match="cannot be bound"):
            transpile(expr_graph(nodes), {("s", "when"): "flag"}, "t")

    def test_polyline_points_mix_literals_and_expressions(self):
        nodes = [
            {"id": "p", "type": "profile_polyline",
             "params": {"plane": "XZ", "points": [[0, 0], [{"expr": "l"}, 0], [0, 5]]}},
            {"id": "e", "type": "extrude", "inputs": {"profile": "p"}, "params": {"height": 2}},
        ]
        script = transpile(expr_graph(nodes, parameters={"l": {"default": 9}}), {}, "t")
        assert ('cq.Workplane("XZ").polyline([(0.0, 0.0), '
                '(_g_float(_g_p_l, "p.points[1][0]"), 0.0), (0.0, 5.0)]).close()') in script

    @pytest.mark.parametrize(("points", "message"), [
        ([[0, 0], [1, 0]], "3.."),
        ([[0, 0], [1, 0], [1]], r"\[x, y\] pair"),
        ([[0, 0], [1, 0], [1, "2"]], "expected a number"),
        ("[[0,0]]", "3.."),
    ])
    def test_polyline_points_are_validated(self, points, message):
        nodes = [{"id": "p", "type": "profile_polyline", "params": {"points": points}},
                 {"id": "e", "type": "extrude", "inputs": {"profile": "p"}}]
        with pytest.raises(GraphError, match=message):
            transpile(expr_graph(nodes), {}, "t")

    def test_revolve_axis_must_lie_in_the_profile_plane(self):
        nodes = [{"id": "p", "type": "profile_circle", "params": {"plane": "XY", "x": 10}},
                 {"id": "r", "type": "revolve", "inputs": {"profile": "p"}, "params": {"axis": "z"}}]
        with pytest.raises(GraphError, match="normal to its profile's XY plane"):
            transpile(expr_graph(nodes), {}, "t")

    def test_revolve_emits_the_bounded_helper(self):
        nodes = [{"id": "p", "type": "profile_circle", "params": {"plane": "XZ", "x": 10}},
                 {"id": "r", "type": "revolve", "inputs": {"profile": "p"}}]
        script = transpile(expr_graph(nodes), {}, "t")
        assert "def _g_revolve(profile, angle, axis, where):" in script
        assert '_n_r = _g_revolve(_n_p, 360.0, (0, 0, 1), "r")' in script

    def test_a_profile_feeds_one_consumer(self):
        nodes = [{"id": "p", "type": "profile_circle"},
                 {"id": "e1", "type": "extrude", "inputs": {"profile": "p"}},
                 {"id": "e2", "type": "extrude", "inputs": {"profile": "p"}},
                 {"id": "u", "type": "union", "inputs": {"a": "e1", "b": "e2"}}]
        with pytest.raises(GraphError, match="feeds both 'e1' and 'e2'"):
            transpile(expr_graph(nodes), {}, "t")


@pytest.mark.skipif(importlib.util.find_spec("jsonschema") is None, reason="jsonschema missing")
class TestSchemaContract:
    def validator(self):
        import jsonschema
        schema = json.loads(SCHEMA.read_text())
        jsonschema.Draft7Validator.check_schema(schema)
        return jsonschema.Draft7Validator(schema)

    def test_schema_lists_every_engine_node_type(self):
        schema = json.loads(SCHEMA.read_text())
        enum = schema["$defs"]["node"]["properties"]["type"]["enum"]
        assert sorted(enum) == sorted(graph_engine.NODE_TYPES)

    def test_a_wave_d_document_validates(self):
        doc = expr_graph(
            [{"id": "p", "type": "profile_polyline",
              "params": {"plane": "XZ", "points": [[1, 0], [{"expr": "w"}, 0], [1, 4]]}},
             {"id": "r", "type": "revolve", "inputs": {"profile": "p"}, "params": {"angle": 360}},
             {"id": "m", "type": "reflect", "inputs": {"shape": "r"}},
             {"id": "s", "type": "select", "inputs": {"if_true": "m", "if_false": "r"},
              "params": {"when": {"expr": "flip"}}}],
            parameters={"w": {"default": 5}, "flip": {"default": False}},
            derived=[{"id": "half", "expr": "w / 2"}],
        )
        assert list(self.validator().iter_errors(doc)) == []

    @pytest.mark.parametrize("bad", [
        {"parameters": {"w": {"default": 1, "min": 0}}},
        {"derived": [{"id": "x"}]},
        {"nodes": [{"id": "b", "type": "box", "params": {"w": {"expr": 3}}}]},
        {"nodes": [{"id": "b", "type": "box", "params": {"w": {"expr": "1", "x": 1}}}]},
    ])
    def test_malformed_wave_d_documents_are_rejected(self, bad):
        doc = {"version": "1.1.0", "nodes": [box()], "outputs": {"part": "b"}, **bad}
        assert list(self.validator().iter_errors(doc))


def render(doc, tmp_path, params=None, part="part"):
    script_path = tmp_path / "graph_script.py"
    script_path.write_text(transpile(doc, {}, "wave_d"))
    out_path = tmp_path / "out.stl"
    result = subprocess.run(
        [sys.executable, str(RUNNER), str(script_path), str(out_path),
         json.dumps({"target_part": part, **(params or {})}), "stl"],
        capture_output=True, text=True, timeout=180, check=False,
    )
    return result, out_path


@pytest.mark.skipif(not HAS_CADQUERY, reason="cadquery not installed")
class TestWaveDRendersThroughTheSandbox:
    """The emitted helpers must run under cq_runner's restricted builtins."""

    def lathe(self, angle=360.0, x="r_in", axis="z"):
        return expr_graph(
            [{"id": "ring", "type": "profile_rect", "params": {
                "plane": "XZ", "w": {"expr": "r_out - r_in"}, "d": {"expr": "4 * unit"},
                "x": {"expr": f"({x} + r_out) / 2"}, "y": 2}},
             {"id": "lathe", "type": "revolve", "inputs": {"profile": "ring"},
              "params": {"angle": angle, "axis": axis}},
             {"id": "flipped", "type": "reflect", "inputs": {"shape": "lathe"}, "params": {"plane": "XY"}},
             {"id": "part", "type": "select", "inputs": {"if_true": "flipped", "if_false": "lathe"},
              "params": {"when": {"expr": "flip"}}}],
            parameters={"r_in": {"default": 5}, "r_out": {"default": 12},
                        "flip": {"default": False}, "size": {"default": "M", "map": {"M": 1}}},
            derived=[{"id": "unit", "expr": "size"}],
        )

    def test_expressions_select_reflect_and_revolve_render(self, tmp_path):
        doc = self.lathe()
        result, out = render(doc, tmp_path, {"r_out": "15", "flip": True})
        assert result.returncode == 0, result.stdout + result.stderr
        assert out.stat().st_size > 500

    def test_polyline_extrude_renders(self, tmp_path):
        doc = expr_graph(
            [{"id": "tri", "type": "profile_polyline",
              "params": {"points": [[0, 0], [{"expr": "leg"}, 0], [0, {"expr": "leg"}]]}},
             {"id": "part", "type": "extrude", "inputs": {"profile": "tri"}, "params": {"height": 3}}],
            parameters={"leg": {"default": 12}},
        )
        result, out = render(doc, tmp_path)
        assert result.returncode == 0, result.stdout + result.stderr
        assert out.stat().st_size > 200

    @pytest.mark.parametrize(("kwargs", "params", "message"), [
        ({"x": "-r_out"}, {}, "crosses its axis"),
        ({"angle": 400.0}, {}, r"\(0, 360\]"),
        ({}, {"r_out": 2000}, "reaches beyond"),
    ])
    def test_revolve_bounds_fail_before_the_kernel(self, tmp_path, kwargs, params, message):
        result, _ = render(self.lathe(**kwargs), tmp_path, params)
        assert result.returncode != 0
        assert re.search(message, result.stdout + result.stderr)

    def test_unmapped_option_fails_loudly(self, tmp_path):
        result, _ = render(self.lathe(), tmp_path, {"size": "XL"})
        assert result.returncode != 0
        assert "not numeric" in result.stdout + result.stderr
