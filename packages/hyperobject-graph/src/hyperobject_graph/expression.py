"""The expression dialect of graph format 1.1, kernel-neutral.

A graph input may be ``{"expr": "width / 2 - wall"}``. The dialect is the one the
manifest constraints already use (Yantra4D ``apps/studio/src/lib/safeFormula.ts``):
numbers, identifiers, ``+ - * / %``, comparisons, ``&& || !``, ``?:`` and parentheses;
no strings, no calls; at most 256 characters and 128 tokens.

This module is a port of the solid engine's parser (``graph_engine.py`` ``_expr_tokenize``
and ``_ExprParser``, vendored at ``y4d_spec/graph/``) with the same tokens, the same
precedence, the same limits and the same syntax-tree shapes, so a formula one accepts is
a formula the other accepts. ``tests/test_graph_core_expression.py`` holds the two to that
by a differential run. It adds what a kernel-neutral core needs and the solid engine keeps
private: the identifiers a formula reads, and an evaluator with the dialect's value
semantics, so the soft and sheet kernels, a configurator and the wrapper lowering can all
compute a value without a CAD kernel.

Value semantics (JavaScript's, carried as Python floats and bools):

* arithmetic and ordering coerce through ``Number()`` (``true`` is 1);
* ``==``/``===`` and ``!=``/``!==`` are strict: a boolean never equals a number;
* ``&&`` and ``||`` return booleans and evaluate both sides, as ``?:`` evaluates both
  branches, so an error on either side is an error;
* ``/`` and ``%`` by zero are errors; ``%`` is the truncating remainder (``math.fmod``);
* truthiness is JavaScript's (0 and NaN are false).

Stdlib only.
"""

from __future__ import annotations

import math

from .errors import GraphCoreError

#: The dialect's own caps (safeFormula.ts MAX_FORMULA_LENGTH / MAX_TOKENS).
MAX_EXPR_LENGTH = 256
MAX_EXPR_TOKENS = 128

_OPERATORS = (
    "===", "!==", "<=", ">=", "&&", "||", "==", "!=", "+", "-", "*", "/", "%", "<", ">", "!",
)
_COMPARISON = frozenset({"<", "<=", ">", ">=", "==", "!=", "===", "!=="})

__all__ = [
    "MAX_EXPR_LENGTH",
    "MAX_EXPR_TOKENS",
    "evaluate",
    "expression_names",
    "is_expression",
    "parse_expression",
    "truthy",
]


def _fail(where: str, message: str) -> GraphCoreError:
    return GraphCoreError(f"{where}: {message}", code="expression")


def tokenize(source: str, where: str = "expression") -> list[tuple[str, str]]:
    """The token list, ending in ``("eof", "")``. Raises on the dialect's limits."""
    if len(source) > MAX_EXPR_LENGTH:
        raise _fail(where, f"expression is too long (max {MAX_EXPR_LENGTH} characters)")
    tokens: list[tuple[str, str]] = []
    index = 0
    length = len(source)
    while index < length:
        char = source[index]
        if char.isspace():
            index += 1
            continue
        nxt = source[index + 1] if index + 1 < length else ""
        if "0" <= char <= "9" or (char == "." and "0" <= nxt <= "9"):
            start = index
            index += 1
            while index < length and "0" <= source[index] <= "9":
                index += 1
            if index < length and source[index] == ".":
                index += 1
                while index < length and "0" <= source[index] <= "9":
                    index += 1
            tokens.append(("number", source[start:index]))
            continue
        if char.isascii() and (char.isalpha() or char in "_$"):
            start = index
            index += 1
            while index < length and source[index].isascii() and (
                source[index].isalnum() or source[index] in "_$"
            ):
                index += 1
            tokens.append(("identifier", source[start:index]))
            continue
        if char in "()?:":
            tokens.append((char, char))
            index += 1
            continue
        operator = next((op for op in _OPERATORS if source.startswith(op, index)), None)
        if operator is None:
            raise _fail(where, f"unsupported token {char!r} in expression")
        tokens.append(("operator", operator))
        index += len(operator)
    if len(tokens) > MAX_EXPR_TOKENS:
        raise _fail(where, f"expression has too many tokens (max {MAX_EXPR_TOKENS})")
    tokens.append(("eof", ""))
    return tokens


class _Parser:
    """Recursive descent, one method per safeFormula.ts method, in the same order."""

    def __init__(self, source: str, where: str):
        self.where = where
        self.tokens = tokenize(source, where)
        self.cursor = 0

    def fail(self, message: str):
        raise _fail(self.where, f"{message} in expression")

    def current(self):
        return self.tokens[self.cursor]

    def match(self, *values):
        kind, value = self.current()
        if kind != "operator" or value not in values:
            return None
        self.cursor += 1
        return value

    def parse(self):
        tree = self.conditional()
        if self.current()[0] != "eof":
            self.fail("unexpected trailing token")
        return tree

    def conditional(self):
        condition = self.logical_or()
        if self.current()[0] != "?":
            return condition
        self.cursor += 1
        when_true = self.conditional()
        if self.current()[0] != ":":
            self.fail("expected conditional separator")
        self.cursor += 1
        when_false = self.conditional()
        return ("if", condition, when_true, when_false)

    def logical_or(self):
        left = self.logical_and()
        while self.match("||"):
            left = ("or", left, self.logical_and())
        return left

    def logical_and(self):
        left = self.comparison()
        while self.match("&&"):
            left = ("and", left, self.comparison())
        return left

    def comparison(self):
        left = self.additive()
        while self.current()[0] == "operator" and self.current()[1] in _COMPARISON:
            operator = self.current()[1]
            self.cursor += 1
            left = ("compare", operator, left, self.additive())
        return left

    def additive(self):
        left = self.multiplicative()
        while True:
            operator = self.match("+", "-")
            if operator is None:
                return left
            left = ("arith", operator, left, self.multiplicative())

    def multiplicative(self):
        left = self.unary()
        while True:
            operator = self.match("*", "/", "%")
            if operator is None:
                return left
            left = ("arith", operator, left, self.unary())

    def unary(self):
        operator = self.match("!", "-", "+")
        if operator is not None:
            return ("unary", operator, self.unary())
        return self.primary()

    def primary(self):
        kind, value = self.current()
        if kind == "number":
            self.cursor += 1
            number = float(value)
            if not math.isfinite(number):
                self.fail("invalid number")
            return ("number", number)
        if kind == "identifier":
            self.cursor += 1
            return ("name", value)
        if kind == "(":
            self.cursor += 1
            tree = self.conditional()
            if self.current()[0] != ")":
                self.fail("expected closing parenthesis")
            self.cursor += 1
            return tree
        self.fail("expected value")
        return None  # pragma: no cover - fail() raises


def is_expression(value: object) -> bool:
    """Is this input an ``{"expr": ...}`` object (well-formed or not)?"""
    return isinstance(value, dict) and "expr" in value


def parse_expression(value: object, where: str = "expression") -> tuple:
    """Parse a formula string, or an ``{"expr": ...}`` object, into its syntax tree.

    The tree is the solid engine's: ``("number", f)``, ``("name", id)``,
    ``("unary", op, t)``, ``("arith", op, l, r)``, ``("compare", op, l, r)``,
    ``("and", l, r)``, ``("or", l, r)`` and ``("if", c, a, b)``.
    """
    if isinstance(value, dict):
        if set(value) != {"expr"}:
            raise _fail(where, "an expression must be an object with one key, 'expr'")
        value = value["expr"]
    if not isinstance(value, str) or not value.strip():
        raise _fail(where, "'expr' must be a non-empty string")
    return _Parser(value, where).parse()


def expression_names(tree: tuple) -> set[str]:
    """Every identifier a syntax tree reads."""
    if tree[0] == "name":
        return {tree[1]}
    if tree[0] == "number":
        return set()
    names: set[str] = set()
    for child in tree[1:]:
        if isinstance(child, tuple):
            names |= expression_names(child)
    return names


def truthy(value: object) -> bool:
    """JavaScript truthiness for the dialect's values (0 and NaN are false)."""
    return bool(value) and not (isinstance(value, float) and math.isnan(value))


def _number(value: object) -> float:
    return float(value)


def evaluate(tree: tuple, env: dict[str, float | bool]) -> float | bool:
    """The value of a syntax tree under ``env`` (identifier → number or boolean).

    Raises ``GraphCoreError`` for an identifier ``env`` lacks and for division by zero,
    the two errors the dialect has at evaluation time.
    """
    head = tree[0]
    if head == "number":
        return tree[1]
    if head == "name":
        if tree[1] not in env:
            raise GraphCoreError(f"expression reads undeclared {tree[1]!r}", code="expression")
        return env[tree[1]]
    if head == "unary":
        inner = evaluate(tree[2], env)
        if tree[1] == "!":
            return not truthy(inner)
        if tree[1] == "-":
            return -_number(inner)
        return _number(inner)
    if head == "arith":
        left = evaluate(tree[2], env)
        right = evaluate(tree[3], env)
        op = tree[1]
        if op in ("/", "%"):
            divisor = _number(right)
            if divisor == 0:
                raise GraphCoreError("Division by zero", code="expression")
            if op == "/":
                return _number(left) / divisor
            dividend = _number(left)
            if not math.isfinite(dividend):
                return math.nan
            return math.fmod(dividend, divisor)
        if op == "+":
            return _number(left) + _number(right)
        if op == "-":
            return _number(left) - _number(right)
        return _number(left) * _number(right)
    if head == "compare":
        left = evaluate(tree[2], env)
        right = evaluate(tree[3], env)
        op = tree[1]
        if op in ("==", "==="):
            return type(left) is type(right) and left == right
        if op in ("!=", "!=="):
            return not (type(left) is type(right) and left == right)
        a, b = _number(left), _number(right)
        return {"<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b}[op]
    if head == "and":
        left = evaluate(tree[1], env)
        right = evaluate(tree[2], env)
        return truthy(left) and truthy(right)
    if head == "or":
        left = evaluate(tree[1], env)
        right = evaluate(tree[2], env)
        return truthy(left) or truthy(right)
    # "if": both branches are evaluated, as the dialect does.
    condition = evaluate(tree[1], env)
    when_true = evaluate(tree[2], env)
    when_false = evaluate(tree[3], env)
    return when_true if truthy(condition) else when_false
