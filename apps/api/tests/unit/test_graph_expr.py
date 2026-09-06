"""
Unit tests for the graph expression dialect (services/engine/graph_expr.py).

`TestSafeFormulaParity` is the important class: it is a line-by-line port of
`apps/studio/src/lib/safeFormula.test.js`, so the browser evaluator and this one
are held to the same accept and reject vectors. A graph author writes the same
dialect the manifest constraints use, and the two implementations must agree on
which expressions are legal, what they evaluate to, and which are refused —
otherwise the Studio would accept an expression the render rejects, or worse,
show a different number than the render produces.

**When you change either evaluator, change both, and keep these vectors in
sync with the JS file.** The two suites are deliberately duplicated rather than
generated: a generator would have to run node from pytest, and the duplication
is cheap next to the cost of a silent divergence.

The remaining classes cover what only the Python side has: compilation to
emitted probe arithmetic, and constant folding.
"""
import math
from typing import ClassVar

import pytest

from services.engine.graph_expr import (
    MAX_FORMULA_LENGTH,
    GraphExprError,
    compile_expression,
    evaluate_expression,
    expression_identifiers,
    is_emittable_identifier,
)


class TestSafeFormulaParity:
    """Ported from apps/studio/src/lib/safeFormula.test.js — accept vectors."""

    def test_evaluates_arithmetic_and_comparison(self):
        assert evaluate_expression(
            "width_units * depth_units <= 24", {"width_units": 4, "depth_units": 6}
        ) is True

    def test_evaluates_grouped_boolean(self):
        assert evaluate_expression(
            "(rows + cols) > 4 && enabled == 1", {"rows": 2, "cols": 3, "enabled": 1}
        ) is True

    def test_evaluates_manifest_ternary_quantity(self):
        assert evaluate_expression(
            "(enable_magnets ? 4 : 0) + (bp_enable_magnets ? 4 * width_units * depth_units : 0)",
            {
                "enable_magnets": True,
                "bp_enable_magnets": True,
                "width_units": 3,
                "depth_units": 2,
            },
        ) == 28

    def test_rejects_unsupported_function_calls(self):
        with pytest.raises(GraphExprError):
            evaluate_expression('constructor.constructor("return process")()', {})

    def test_rejects_missing_numeric_parameters(self):
        with pytest.raises(GraphExprError):
            evaluate_expression("rows * cols", {"rows": 2})

    @pytest.mark.parametrize(
        ("formula", "expected"),
        [
            ("1 + 2", 3),
            ("5 - 8", -3),
            ("3 * 4", 12),
            ("9 / 2", 4.5),
            ("7 % 3", 1),
            ("2 < 3", True),
            ("3 <= 3", True),
            ("4 > 5", False),
            ("5 >= 5", True),
            ("2 == 2", True),
            ("2 === 2", True),
            ("2 != 3", True),
            ("2 !== 3", True),
            ("1 && 0", False),
            ("0 || 3", True),
            ("!0", True),
            ("-4 + 10", 6),
            ("+3", 3),
            ("!!1", True),
        ],
    )
    def test_operators(self, formula, expected):
        result = evaluate_expression(formula, {})
        assert result == expected
        # Booleans and numbers must not blur into each other, exactly as
        # `toBe` distinguishes them in the JS suite.
        assert isinstance(result, bool) == isinstance(expected, bool)

    def test_respects_precedence_without_parentheses(self):
        assert evaluate_expression("2 + 3 * 4", {}) == 14

    def test_parses_decimals_with_and_without_leading_digit(self):
        assert evaluate_expression("0.5 + .25", {}) == 0.75

    @pytest.mark.parametrize(("a", "expected"), [(5, 3), (3, 2), (1, 1)])
    def test_nests_ternaries(self, a, expected):
        assert evaluate_expression("a > 2 ? (a > 4 ? 3 : 2) : 1", {"a": a}) == expected

    # ── parameter coercion ────────────────────────────────────────────────────

    def test_accepts_booleans(self):
        assert evaluate_expression("flag ? 1 : 0", {"flag": True}) == 1

    def test_accepts_numeric_strings(self):
        assert evaluate_expression("n + 1", {"n": "41"}) == 42

    def test_rejects_a_non_numeric_string(self):
        with pytest.raises(GraphExprError, match="Missing numeric parameter"):
            evaluate_expression("n + 1", {"n": "wide"})

    def test_rejects_a_blank_string(self):
        with pytest.raises(GraphExprError, match="Missing numeric parameter"):
            evaluate_expression("n + 1", {"n": "   "})

    def test_rejects_none(self):
        with pytest.raises(GraphExprError):
            evaluate_expression("n", {"n": None})

    def test_rejects_absent(self):
        with pytest.raises(GraphExprError):
            evaluate_expression("n", {})

    # ── malformed input ───────────────────────────────────────────────────────

    @pytest.mark.parametrize(
        ("name", "formula", "params"),
        [
            ("unbalanced parenthesis", "(1 + 2", {}),
            ("trailing token", "1 + 2 3", {}),
            ("empty formula", "", {}),
            ("dangling operator", "1 +", {}),
            ("ternary without a colon", "a ? 1", {"a": 1}),
            ("unsupported character", "1 # 2", {}),
            ("bare closing parenthesis", ")", {}),
        ],
    )
    def test_rejects_malformed(self, name, formula, params):
        with pytest.raises(GraphExprError):
            evaluate_expression(formula, params)

    def test_division_by_zero(self):
        with pytest.raises(GraphExprError, match="Division by zero"):
            evaluate_expression("1 / 0", {})

    def test_modulo_by_zero(self):
        with pytest.raises(GraphExprError, match="Division by zero"):
            evaluate_expression("1 % 0", {})

    def test_formula_longer_than_the_limit(self):
        with pytest.raises(GraphExprError, match="too long"):
            evaluate_expression("1 +" * 200 + "1", {})

    def test_formula_with_more_tokens_than_the_limit(self):
        # Under the 256-char cap but over the 128-token cap.
        source = "1+" * 80 + "1"
        assert len(source) <= MAX_FORMULA_LENGTH
        with pytest.raises(GraphExprError, match="too many tokens"):
            evaluate_expression(source, {})

    # ── sandbox escapes ───────────────────────────────────────────────────────

    @pytest.mark.parametrize(
        ("name", "formula"),
        [
            ("property access", "a.b"),
            ("bracket access", 'a["b"]'),
            ("assignment", "a = 1"),
            ("sequence", "1, 2"),
            ("template literal", "`x`"),
            ("arrow function", "() => 1"),
            ("prototype reach", "__proto__"),
        ],
    )
    def test_resists_sandbox_escapes(self, name, formula):
        with pytest.raises(GraphExprError):
            evaluate_expression(formula, {"a": 1})


class TestCapBoundaries:
    """The caps are inclusive on the legal side, not just exclusive above it."""

    def test_exactly_at_the_length_cap_is_accepted(self):
        source = "1" + " + 1" * 20
        source = source + " " * (MAX_FORMULA_LENGTH - len(source))
        assert len(source) == MAX_FORMULA_LENGTH
        assert evaluate_expression(source, {}) == 21

    def test_exactly_at_the_token_cap_is_accepted(self):
        # 64 numbers + 63 operators = 127 tokens, counted before `eof` is
        # appended and so under the 128 cap; 100 numbers is 199 and over it.
        source = "+".join(["1"] * 64)
        assert evaluate_expression(source, {}) == 64
        with pytest.raises(GraphExprError, match="too many tokens"):
            evaluate_expression("+".join(["1"] * 100), {})

    def test_a_number_larger_than_the_cap_is_a_length_error_first(self):
        with pytest.raises(GraphExprError, match="too long"):
            evaluate_expression("9" * (MAX_FORMULA_LENGTH + 1), {})


class TestJavaScriptSemantics:
    """Where Python and JavaScript disagree, the JS answer is the right one."""

    def test_strict_equality_does_not_conflate_boolean_and_number(self):
        # In Python `True == 1`; in the JS dialect `===` says otherwise, and
        # safeFormula.ts uses `===` for both `==` and `===`.
        assert evaluate_expression("flag == 1", {"flag": True}) is False
        assert evaluate_expression("flag != 1", {"flag": True}) is True

    def test_boolean_coerces_to_a_number_in_arithmetic(self):
        assert evaluate_expression("flag + 1", {"flag": True}) == 2
        assert evaluate_expression("flag + 1", {"flag": False}) == 1

    def test_negative_modulo_follows_javascript_not_python(self):
        # Python's `-7 % 3` is 2; JavaScript's is -1.
        assert evaluate_expression("-7 % 3", {}) == -1

    def test_true_division_never_floors(self):
        assert evaluate_expression("7 / 2", {}) == 3.5

    def test_bang_yields_a_boolean_not_a_number(self):
        assert evaluate_expression("!x", {"x": 0}) is True
        assert evaluate_expression("!x", {"x": 5}) is False

    def test_logical_operators_yield_booleans(self):
        # JS `0 || 3` is 3, but safeFormula.ts coerces with Boolean() on both
        # sides and returns a boolean — the test vector `['0 || 3', true]`
        # pins that, and this port must not "improve" on it.
        assert evaluate_expression("0 || 3", {}) is True
        assert evaluate_expression("2 && 3", {}) is True


class TestIdentifierHelpers:
    def test_lists_identifiers_in_first_appearance_order(self):
        assert expression_identifiers("b + a * b - c") == ["b", "a", "c"]

    def test_lists_no_identifiers_for_pure_arithmetic(self):
        assert expression_identifiers("1 + 2 * 3") == []

    def test_a_malformed_expression_still_raises(self):
        with pytest.raises(GraphExprError):
            expression_identifiers("1 # 2")

    @pytest.mark.parametrize(
        ("name", "ok"),
        [("width", True), ("bolt_count", True), ("_hidden", True), ("a$b", False), ("$x", False)],
    )
    def test_emittable_identifiers(self, name, ok):
        assert is_emittable_identifier(name) is ok


class TestCompilation:
    """compile_expression emits Python over caller-supplied probe fragments."""

    @staticmethod
    def _live(name):
        """Resolve every identifier to a live probe (never a constant)."""
        return (f"_param(lambda: {name}, 0.0)", None)

    def test_folds_a_literal_expression_to_a_constant(self):
        code, is_constant, constant = compile_expression("2 + 3 * 4", self._live)
        assert is_constant and constant == 14
        assert code == "14"

    def test_a_live_identifier_prevents_folding(self):
        code, is_constant, constant = compile_expression("360 / n", self._live)
        assert not is_constant and constant is None
        assert "_param(lambda: n, 0.0)" in code
        assert "_expr_div" in code

    def test_no_source_text_survives_into_the_emitted_code(self):
        # The author's spacing, redundant parentheses and operator spelling are
        # all discarded — the output is rebuilt from the parse, never spliced.
        code, _flag, _constant = compile_expression("(  n   ===   2  )", self._live)
        assert "===" not in code
        assert "  " not in code

    def test_a_constant_condition_selects_a_branch_at_compile_time(self):
        code, is_constant, _c = compile_expression("1 ? n : 99", self._live)
        assert not is_constant
        assert "99" not in code
        _code, is_constant, constant = compile_expression("0 ? n : 99", self._live)
        assert is_constant and constant == 99

    def test_a_folded_boolean_stays_a_boolean(self):
        code, is_constant, constant = compile_expression("2 > 1", self._live)
        assert is_constant and constant is True
        assert code == "True"

    def test_unknown_identifiers_propagate_the_resolver_error(self):
        def refuse(name):
            raise GraphExprError(f"Missing numeric parameter: {name}")

        with pytest.raises(GraphExprError, match="Missing numeric parameter: n"):
            compile_expression("n + 1", refuse)

    def test_the_caps_apply_to_compilation_too(self):
        with pytest.raises(GraphExprError, match="too long"):
            compile_expression("1 +" * 200 + "1", self._live)

    @pytest.mark.parametrize(
        "formula",
        ["a.b", 'a["b"]', "a = 1", "1, 2", "`x`", "() => 1", "1 # 2", "(1 + 2"],
    )
    def test_malformed_input_never_compiles(self, formula):
        with pytest.raises(GraphExprError):
            compile_expression(formula, self._live)


class TestCompiledCodeMatchesTheEvaluator:
    """The emitted Python must produce what the folding evaluator produces.

    This is the property that makes an expression safe to leave live: a graph
    author reasons about one dialect, and gets the same number whether the
    value folded at transpile time or was recomputed in the render worker.
    """

    RUNTIME: ClassVar[dict] = {
        "_expr_num": lambda v: (1.0 if v else 0.0) if isinstance(v, bool) else float(v),
        "_expr_bool": lambda v: v if isinstance(v, bool) else v != 0,
        "_expr_eq": lambda a, b: type(a) is type(b) and a == b,
        "_expr_div": lambda a, b: a / b,
        "_expr_mod": lambda a, b: math.fmod(a, b),
    }

    CASES: ClassVar[list] = [
        ("360 / n", {"n": 6}),
        ("n * 2 + 1", {"n": 3.5}),
        ("n > 4 ? n * 2 : n / 2", {"n": 5}),
        ("n > 4 ? n * 2 : n / 2", {"n": 2}),
        ("!n", {"n": 0}),
        ("-n + 10", {"n": 4}),
        ("n % 4", {"n": 7}),
        ("n % 4", {"n": -7}),
        ("(a + b) * 2", {"a": 1.5, "b": 2.5}),
        ("a >= b && a != b", {"a": 3, "b": 2}),
        ("a == b", {"a": 2, "b": 2}),
        ("flag ? a : b", {"flag": True, "a": 1, "b": 2}),
    ]

    @pytest.mark.parametrize(("formula", "params"), CASES)
    def test_emitted_code_agrees_with_evaluate(self, formula, params):
        expected = evaluate_expression(formula, params)

        def resolve(name):
            return (f"_values[{name!r}]", None)

        code, is_constant, _constant = compile_expression(formula, resolve)
        assert not is_constant, "these cases all reference a live parameter"
        scope = dict(self.RUNTIME)
        scope["_values"] = params
        # The generated script runs this same code under cq_runner's globals.
        # eval on code this module generated from a parsed expression — never
        # on author text — under builtins reduced to what the runtime needs.
        actual = eval(
            code,
            {"__builtins__": {"isinstance": isinstance, "type": type, "float": float, "bool": bool}},
            scope,
        )
        assert actual == expected
        assert isinstance(actual, bool) == isinstance(expected, bool)


class TestFalsyFoldsAreStillConstants:
    """`0` and `False` fold like any other value.

    Reported as a flag rather than `constant is not None`, because the engine
    range-checks a folded value against the param's kind — and a `0` mistaken
    for "live" would skip that check and emit an unclamped probe chain instead.
    """

    @staticmethod
    def _live(name):
        return (f"_param(lambda: {name}, 0.0)", None)

    @pytest.mark.parametrize(
        ("formula", "expected"),
        [("1 - 1", 0), ("0", 0), ("5 - 5", 0), ("2 > 3", False), ("!1", False), ("0 * 7", 0)],
    )
    def test_a_falsy_result_is_reported_as_constant(self, formula, expected):
        _code, is_constant, constant = compile_expression(formula, self._live)
        assert is_constant is True
        assert constant == expected
        assert isinstance(constant, bool) == isinstance(expected, bool)

    def test_a_live_expression_is_reported_as_not_constant(self):
        _code, is_constant, constant = compile_expression("n - n", self._live)
        # Not folded: the compiler does no algebra, only constant arithmetic.
        assert is_constant is False
        assert constant is None
