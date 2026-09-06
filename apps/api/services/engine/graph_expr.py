"""
Graph expression dialect — a Python port of the Studio's `safeFormula.ts`.

A graph node input may be written `{"expr": "360 / bolt_count"}` instead of a
literal or a `{"param": id}` binding. This module parses that expression and
either folds it to a number (when nothing in it is live) or compiles it to a
Python expression over `_param(...)` probes, which the graph engine emits into
the generated CadQuery script.

**The dialect is the manifest-constraint dialect, deliberately.** Authors
already write `width_units * depth_units <= 24` in manifest constraints, and
`apps/studio/src/lib/safeFormula.ts` is the evaluator that runs them in the
browser. A second, subtly different grammar for graph sockets would be a bug
farm, so this is a port rather than a new design, and
`tests/unit/test_graph_expr.py` re-runs `safeFormula.test.js`'s own accept and
reject vectors against this implementation to keep the two honest.

What the dialect is: numeric and boolean literals via identifiers, arithmetic
(`+ - * / %`), comparison (`< <= > >= == != === !==`), boolean (`&& || !`),
a ternary (`c ? a : b`), and parentheses. What it is NOT, by construction:
there are no string literals, no property access, no indexing, no assignment,
no commas, and **no function calls** — the tokenizer has no token for any of
them, so `constructor.constructor("return process")()` dies at `.` rather than
being caught by a denylist. Two caps bound the work: 256 characters and 128
tokens, both checked before parsing.

Security note: this module never calls `eval`. `compile_expression` returns
Python source text assembled from validated numeric literals, operator
punctuation and `_param(lambda: <validated identifier>, <numeric literal>)`
probes — no fragment of the author's text is ever interpolated into the output.
An unknown identifier and a syntax error are both hard `GraphExprError`s: an
expression that cannot be understood must never degrade into a silent literal.

Standard library only, deliberately: `hyperobjects-spec` vendors this module
alongside `graph_engine.py` so the keystone can transpile graphs with the same
code the platform runs (Wave D5).
"""
from __future__ import annotations

import math
import re

MAX_FORMULA_LENGTH = 256
MAX_TOKENS = 128

# Longest-first: '===' must win over '==' must win over '='-less '=' (absent).
OPERATORS = ("===", "!==", "<=", ">=", "&&", "||", "==", "!=", "+", "-", "*", "/", "%", "<", ">", "!")

_DIGIT_RE = re.compile(r"[0-9]")
_IDENT_START_RE = re.compile(r"[A-Za-z_$]")
_IDENT_PART_RE = re.compile(r"[A-Za-z0-9_$]")
_WHITESPACE_RE = re.compile(r"\s")

# Identifiers that survive into emitted Python. `$` is legal in the JS dialect
# and in a manifest parameter id it would not be, but the tokenizer accepts it
# so both evaluators agree on *tokenizing*; an identifier containing `$` simply
# never resolves and fails as an unknown identifier.
_EMITTABLE_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class GraphExprError(ValueError):
    """Raised when an expression is malformed or references something unknown."""


class _Token:
    __slots__ = ("type", "value")

    def __init__(self, type_: str, value: str) -> None:
        self.type = type_
        self.value = value

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"_Token({self.type!r}, {self.value!r})"


def tokenize(source: str) -> list[_Token]:
    """Split an expression into tokens, or raise. Mirrors safeFormula.ts."""
    if not isinstance(source, str):
        raise GraphExprError(f"expression must be a string, got {type(source).__name__}")
    if len(source) > MAX_FORMULA_LENGTH:
        raise GraphExprError("Formula is too long")

    tokens: list[_Token] = []
    index = 0
    length = len(source)

    while index < length:
        char = source[index]

        if _WHITESPACE_RE.match(char):
            index += 1
            continue

        # A number, including the leading-dot form (".25").
        if _DIGIT_RE.match(char) or (
            char == "." and index + 1 < length and _DIGIT_RE.match(source[index + 1])
        ):
            start = index
            index += 1
            while index < length and _DIGIT_RE.match(source[index]):
                index += 1
            if index < length and source[index] == ".":
                index += 1
                while index < length and _DIGIT_RE.match(source[index]):
                    index += 1
            tokens.append(_Token("number", source[start:index]))
            continue

        if _IDENT_START_RE.match(char):
            start = index
            index += 1
            while index < length and _IDENT_PART_RE.match(source[index]):
                index += 1
            tokens.append(_Token("identifier", source[start:index]))
            continue

        if char == "(":
            tokens.append(_Token("leftParen", char))
            index += 1
            continue
        if char == ")":
            tokens.append(_Token("rightParen", char))
            index += 1
            continue
        if char == "?":
            tokens.append(_Token("question", char))
            index += 1
            continue
        if char == ":":
            tokens.append(_Token("colon", char))
            index += 1
            continue

        operator = next((op for op in OPERATORS if source.startswith(op, index)), None)
        if operator is None:
            raise GraphExprError(f"Unsupported token: {char}")
        tokens.append(_Token("operator", operator))
        index += len(operator)

    if len(tokens) > MAX_TOKENS:
        raise GraphExprError("Formula has too many tokens")

    tokens.append(_Token("eof", ""))
    return tokens


# ── JavaScript value semantics ────────────────────────────────────────────────
# The two evaluators must agree on results, not just on which inputs they
# accept, so the arithmetic below reproduces JS coercion rather than Python's.


def _js_number(value) -> float:
    """`Number(value)` for the values this dialect can hold."""
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    return float(value)


def _js_truthy(value) -> bool:
    """`Boolean(value)`; 0 and false are the only falsy values here."""
    if isinstance(value, bool):
        return value
    return value != 0


def _norm(value):
    """Present an integral float as an int so `==` compares like JS `===`.

    JS has one number type, so `2 === 2` holds for `2` written either way.
    Python distinguishes 2 from 2.0 for `is`-like purposes but not for `==`,
    which is what we use — this normalisation exists so the *emitted* Python
    also reads naturally (`6` rather than `6.0` for a whole number).
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, float) and value.is_integer() and abs(value) < 2**53:
        return int(value)
    return value


class _Parser:
    """Recursive-descent parser with safeFormula.ts's precedence, exactly.

    `resolve` maps an identifier to a value. It raises GraphExprError for an
    identifier it does not know, so the parser never invents one.
    """

    def __init__(self, source: str, resolve) -> None:
        self.tokens = tokenize(source)
        self.resolve = resolve
        self.cursor = 0

    def parse(self):
        result = self.parse_conditional()
        if self.current().type != "eof":
            raise GraphExprError("Unexpected trailing token")
        return result

    def current(self) -> _Token:
        return self.tokens[self.cursor]

    def consume(self, value: str | None = None) -> _Token:
        token = self.current()
        if value is not None and token.value != value:
            raise GraphExprError(f"Expected {value}")
        self.cursor += 1
        return token

    def match(self, *values: str) -> bool:
        token = self.current()
        if token.type != "operator" or token.value not in values:
            return False
        self.cursor += 1
        return True

    def parse_conditional(self):
        condition = self.parse_or()
        if self.current().type != "question":
            return condition
        self.consume("?")
        when_true = self.parse_conditional()
        if self.current().type != "colon":
            raise GraphExprError("Expected conditional separator")
        self.consume(":")
        when_false = self.parse_conditional()
        return self.on_conditional(condition, when_true, when_false)

    def parse_or(self):
        left = self.parse_and()
        while self.match("||"):
            left = self.on_logical("||", left, self.parse_and())
        return left

    def parse_and(self):
        left = self.parse_comparison()
        while self.match("&&"):
            left = self.on_logical("&&", left, self.parse_comparison())
        return left

    _COMPARISONS = ("<", "<=", ">", ">=", "==", "!=", "===", "!==")

    def parse_comparison(self):
        left = self.parse_additive()
        while self.current().type == "operator" and self.current().value in self._COMPARISONS:
            operator = self.consume().value
            left = self.on_comparison(operator, left, self.parse_additive())
        return left

    def parse_additive(self):
        left = self.parse_multiplicative()
        while self.current().type == "operator" and self.current().value in ("+", "-"):
            operator = self.consume().value
            left = self.on_additive(operator, left, self.parse_multiplicative())
        return left

    def parse_multiplicative(self):
        left = self.parse_unary()
        while self.current().type == "operator" and self.current().value in ("*", "/", "%"):
            operator = self.consume().value
            left = self.on_multiplicative(operator, left, self.parse_unary())
        return left

    def parse_unary(self):
        if self.match("!"):
            return self.on_unary("!", self.parse_unary())
        if self.match("-"):
            return self.on_unary("-", self.parse_unary())
        if self.match("+"):
            return self.on_unary("+", self.parse_unary())
        return self.parse_primary()

    def parse_primary(self):
        token = self.current()

        if token.type == "number":
            self.consume()
            value = float(token.value)
            if not math.isfinite(value):
                raise GraphExprError("Invalid number")
            return self.on_number(value)

        if token.type == "identifier":
            self.consume()
            return self.on_identifier(token.value)

        if token.type == "leftParen":
            self.consume("(")
            value = self.parse_conditional()
            if self.current().type != "rightParen":
                raise GraphExprError("Expected closing parenthesis")
            self.consume(")")
            return value

        raise GraphExprError("Expected value")

    # Hooks — the evaluating and compiling parsers differ only in these.
    def on_number(self, value: float):
        raise NotImplementedError  # pragma: no cover

    def on_identifier(self, name: str):
        raise NotImplementedError  # pragma: no cover

    def on_unary(self, operator: str, operand):
        raise NotImplementedError  # pragma: no cover

    def on_multiplicative(self, operator: str, left, right):
        raise NotImplementedError  # pragma: no cover

    def on_additive(self, operator: str, left, right):
        raise NotImplementedError  # pragma: no cover

    def on_comparison(self, operator: str, left, right):
        raise NotImplementedError  # pragma: no cover

    def on_logical(self, operator: str, left, right):
        raise NotImplementedError  # pragma: no cover

    def on_conditional(self, condition, when_true, when_false):
        raise NotImplementedError  # pragma: no cover


class _Evaluator(_Parser):
    """Folds the expression to a number or boolean as it parses."""

    def on_number(self, value: float):
        return _norm(value)

    def on_identifier(self, name: str):
        return _norm(self.resolve(name))

    def on_unary(self, operator: str, operand):
        if operator == "!":
            return not _js_truthy(operand)
        if operator == "-":
            return _norm(-_js_number(operand))
        return _norm(_js_number(operand))

    def on_multiplicative(self, operator: str, left, right):
        right_num = _js_number(right)
        left_num = _js_number(left)
        if operator in ("/", "%") and right_num == 0:
            raise GraphExprError("Division by zero")
        if operator == "*":
            return _norm(left_num * right_num)
        if operator == "/":
            return _norm(left_num / right_num)
        return _norm(math.fmod(left_num, right_num))

    def on_additive(self, operator: str, left, right):
        if operator == "+":
            return _norm(_js_number(left) + _js_number(right))
        return _norm(_js_number(left) - _js_number(right))

    def on_comparison(self, operator: str, left, right):
        if operator == "<":
            return _js_number(left) < _js_number(right)
        if operator == "<=":
            return _js_number(left) <= _js_number(right)
        if operator == ">":
            return _js_number(left) > _js_number(right)
        if operator == ">=":
            return _js_number(left) >= _js_number(right)
        # `==` and `===` are both JS strict equality here: a boolean never
        # equals a number, matching safeFormula.ts, which uses `===` for both.
        equal = type(left) is type(right) and left == right
        return equal if operator in ("==", "===") else not equal

    def on_logical(self, operator: str, left, right):
        if operator == "&&":
            return _js_truthy(left) and _js_truthy(right)
        return _js_truthy(left) or _js_truthy(right)

    def on_conditional(self, condition, when_true, when_false):
        return when_true if _js_truthy(condition) else when_false


def evaluate_expression(source: str, params: dict) -> float | int | bool:
    """Evaluate an expression against a mapping of identifier → value.

    Coercion matches safeFormula.ts: numbers and booleans pass through, a
    numeric string is parsed, and anything else (including a blank string,
    None, or a missing key) is a hard error.
    """

    def resolve(name: str):
        if name not in params:
            raise GraphExprError(f"Missing numeric parameter: {name}")
        value = params[name]
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            if not math.isfinite(float(value)):
                raise GraphExprError(f"Missing numeric parameter: {name}")
            return value
        if isinstance(value, str) and value.strip() != "":
            try:
                parsed = float(value)
            except ValueError:
                raise GraphExprError(f"Missing numeric parameter: {name}") from None
            if math.isfinite(parsed):
                return parsed
        raise GraphExprError(f"Missing numeric parameter: {name}")

    return _Evaluator(source, resolve).parse()


# ── Compilation to emitted Python ─────────────────────────────────────────────


class _Fragment:
    """A piece of emitted Python plus the constant it folds to, if any.

    `code` is always valid, fully parenthesised Python. `constant` is the value
    when the whole sub-expression is literal — the transpiler uses it to emit
    `6` instead of a probe arithmetic chain when nothing can change at render
    time.

    Constant-ness is carried by an explicit flag rather than inferred from
    `constant is not None`: `0` and `False` are perfectly good folded values,
    and a caller that tested for None would silently treat `{"expr": "1 - 1"}`
    as live and skip the range check a literal `0` would fail.
    """

    __slots__ = ("code", "constant", "is_constant")

    def __init__(self, code: str, constant=None, *, is_constant: bool | None = None) -> None:
        self.code = code
        self.constant = constant
        self.is_constant = (constant is not None) if is_constant is None else is_constant


def _literal_code(value) -> str:
    if isinstance(value, bool):
        return "True" if value else "False"
    return repr(value)


def _fold(value) -> _Fragment:
    value = _norm(value)
    return _Fragment(_literal_code(value), value, is_constant=True)


class _Compiler(_Parser):
    """Emits Python source, folding constant sub-expressions as it goes.

    Every emitted operation mirrors the JS semantics of `_Evaluator` — the
    helpers `_expr_num`, `_expr_bool` and `_expr_eq` are defined in the
    generated script's preamble so the runtime behaves the same way.
    """

    def on_number(self, value: float):
        return _fold(value)

    def on_identifier(self, name: str):
        # `resolve` returns either a probe fragment (live parameter) or a
        # constant fragment; it raises for anything it does not know.
        return self.resolve(name)

    def _binary(self, left: _Fragment, right: _Fragment, fold, code: str) -> _Fragment:
        if left.is_constant and right.is_constant:
            return _fold(fold(left.constant, right.constant))
        return _Fragment(code, is_constant=False)

    def on_unary(self, operator: str, operand: _Fragment):
        if operand.is_constant:
            if operator == "!":
                folded = not _js_truthy(operand.constant)
                return _Fragment(_literal_code(folded), folded, is_constant=True)
            if operator == "-":
                return _fold(-_js_number(operand.constant))
            return _fold(_js_number(operand.constant))
        if operator == "!":
            return _Fragment(f"(not _expr_bool({operand.code}))", is_constant=False)
        if operator == "-":
            return _Fragment(f"(-_expr_num({operand.code}))", is_constant=False)
        return _Fragment(f"(+_expr_num({operand.code}))", is_constant=False)

    def on_multiplicative(self, operator: str, left: _Fragment, right: _Fragment):
        if left.is_constant and right.is_constant:
            return _fold(_Evaluator.on_multiplicative(self, operator, left.constant, right.constant))
        if operator == "*":
            return _Fragment(f"(_expr_num({left.code}) * _expr_num({right.code}))", is_constant=False)
        if operator == "/":
            return _Fragment(f"_expr_div(_expr_num({left.code}), _expr_num({right.code}))", is_constant=False)
        return _Fragment(f"_expr_mod(_expr_num({left.code}), _expr_num({right.code}))", is_constant=False)

    def on_additive(self, operator: str, left: _Fragment, right: _Fragment):
        symbol = "+" if operator == "+" else "-"
        return self._binary(
            left, right,
            lambda a, b: _Evaluator.on_additive(self, operator, a, b),
            f"(_expr_num({left.code}) {symbol} _expr_num({right.code}))",
        )

    def on_comparison(self, operator: str, left: _Fragment, right: _Fragment):
        if left.is_constant and right.is_constant:
            value = _Evaluator.on_comparison(self, operator, left.constant, right.constant)
            return _Fragment(_literal_code(value), value, is_constant=True)
        if operator in ("==", "===", "!=", "!=="):
            negate = "not " if operator in ("!=", "!==") else ""
            return _Fragment(f"({negate}_expr_eq({left.code}, {right.code}))", is_constant=False)
        return _Fragment(f"(_expr_num({left.code}) {operator} _expr_num({right.code}))", is_constant=False)

    def on_logical(self, operator: str, left: _Fragment, right: _Fragment):
        if left.is_constant and right.is_constant:
            value = _Evaluator.on_logical(self, operator, left.constant, right.constant)
            return _Fragment(_literal_code(value), value, is_constant=True)
        joiner = "and" if operator == "&&" else "or"
        return _Fragment(f"(_expr_bool({left.code}) {joiner} _expr_bool({right.code}))", is_constant=False)

    def on_conditional(self, condition: _Fragment, when_true: _Fragment, when_false: _Fragment):
        if condition.is_constant:
            return when_true if _js_truthy(condition.constant) else when_false
        return _Fragment(
            f"({when_true.code} if _expr_bool({condition.code}) else {when_false.code})",
            is_constant=False,
        )


# The runtime half of the dialect, emitted once into every generated script that
# uses an expression. It is the exact mirror of `_js_number`/`_js_truthy`/`_norm`
# above, so a folded constant and a live probe agree on the same inputs.
EXPR_RUNTIME_LINES = (
    "def _expr_num(value):",
    "    if isinstance(value, bool):",
    "        return 1.0 if value else 0.0",
    "    return float(value)",
    "",
    "",
    "def _expr_bool(value):",
    "    if isinstance(value, bool):",
    "        return value",
    "    return value != 0",
    "",
    "",
    "def _expr_eq(left, right):",
    "    return type(left) is type(right) and left == right",
    "",
    "",
    "def _expr_div(left, right):",
    "    if right == 0:",
    "        raise ValueError(\"Division by zero in a graph expression\")",
    "    return left / right",
    "",
    "",
    "def _expr_mod(left, right):",
    "    if right == 0:",
    "        raise ValueError(\"Division by zero in a graph expression\")",
    "    return math.fmod(left, right)",
)


def compile_expression(source: str, resolve_identifier) -> tuple[str, bool, object]:
    """Compile an expression to Python source over `_param` probes.

    `resolve_identifier(name)` returns a pair ``(code, constant_or_None)``
    describing how that identifier is read — `None` for a live parameter — or
    raises `GraphExprError` if the identifier is unknown.

    Returns ``(code, is_constant, constant)``. `is_constant` is a flag rather
    than `constant is not None` because `0` and `False` are legitimate folded
    values: a caller testing for None would treat `{"expr": "1 - 1"}` as live
    and skip the range check a literal `0` would fail.

    The returned code is assembled solely from numeric literals, operator
    punctuation and the caller's own probe fragments; no character of `source`
    survives into it.
    """

    def resolve(name: str) -> _Fragment:
        code, constant = resolve_identifier(name)
        return _Fragment(code, constant, is_constant=constant is not None)

    fragment = _Compiler(source, resolve).parse()
    return fragment.code, fragment.is_constant, fragment.constant


def expression_identifiers(source: str) -> list[str]:
    """Every identifier an expression reads, in first-appearance order.

    Used by validation to report all unknown names at once rather than only
    the first the parser happens to reach.
    """
    seen: list[str] = []
    for token in tokenize(source):
        if token.type == "identifier" and token.value not in seen:
            seen.append(token.value)
    return seen


def is_emittable_identifier(name: str) -> bool:
    """Can this identifier become a Python name in the generated script?

    The JS dialect allows `$`, which Python does not. Such an identifier can
    never resolve to a manifest parameter (their ids are plain identifiers), so
    it is reported as unknown rather than emitted.
    """
    return bool(_EMITTABLE_IDENT_RE.match(name))
