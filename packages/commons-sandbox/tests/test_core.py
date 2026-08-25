"""Tests for the shared sandbox security core.

This is security-critical code with ONE authored source, so its guarantees are
tested here directly: the whitelist admits only safe builtins, the blocklist +
import guard actually stop dangerous imports, the reflection builtins are
restricted, and the path validator normalizes real paths.
"""

import os

import commons_sandbox as cs
import pytest


# ── the whitelist ────────────────────────────────────────────────────────────
def test_safe_builtins_excludes_capability_granting_names():
    # The builtins that grant file/network/code capability must NOT be present.
    for forbidden in ("open", "eval", "exec", "compile", "__import__", "getattr",
                      "setattr", "globals", "locals", "vars", "input", "exit",
                      "memoryview", "object", "super"):
        assert forbidden not in cs.SAFE_BUILTINS, f"{forbidden} must not be whitelisted"


def test_safe_builtins_includes_pure_computation():
    for ok in ("len", "range", "sum", "sorted", "min", "max", "abs", "zip"):
        assert ok in cs.SAFE_BUILTINS


def test_build_sandbox_builtins_is_a_copy_with_import():
    b = cs.build_sandbox_builtins("Test")
    assert "__import__" in b
    b["poison"] = 1
    assert "poison" not in cs.SAFE_BUILTINS   # mutating the copy doesn't leak


# ── the blocklist + import guard ─────────────────────────────────────────────
def test_restricted_import_blocks_dangerous_modules():
    guard = cs.make_restricted_import("Test scripts")
    for mod in ("os", "sys", "subprocess", "socket", "ctypes", "pickle", "importlib"):
        with pytest.raises(ImportError) as exc:
            guard(mod)
        assert "not allowed" in str(exc.value)
        assert "Test scripts" in str(exc.value)


def test_restricted_import_blocks_submodule_by_top_package():
    guard = cs.make_restricted_import()
    with pytest.raises(ImportError):
        guard("os.path")          # blocked by its top package `os`
    with pytest.raises(ImportError):
        guard("urllib.request")


def test_restricted_import_allows_safe_modules():
    guard = cs.make_restricted_import()
    assert guard("math") is not None
    assert guard("json") is not None


def test_blocked_modules_covers_the_expected_set():
    for m in ("os", "sys", "subprocess", "shutil", "socket", "http", "urllib",
              "importlib", "ctypes", "signal", "multiprocessing", "threading",
              "pickle", "shelve"):
        assert m in cs.BLOCKED_MODULES


# ── restricted reflection ────────────────────────────────────────────────────
def test_safe_type_blocks_three_arg_metaclass_form():
    assert cs.safe_type(5) is int
    with pytest.raises(TypeError):
        cs.safe_type("X", (), {})     # the class-synthesis form is refused


def test_safe_isinstance_and_issubclass_still_work():
    assert cs.safe_isinstance(5, int) is True
    assert cs.safe_issubclass(bool, int) is True


# ── path validation (the healed drift) ───────────────────────────────────────
def test_validate_script_path_accepts_allowed_suffix(tmp_path):
    p = tmp_path / "main.py"
    p.write_text("x = 1\n")
    real = cs.validate_script_path(str(p), {".py"})
    assert real == os.path.realpath(str(p))


def test_validate_script_path_rejects_bad_suffix(tmp_path):
    p = tmp_path / "main.txt"
    p.write_text("x = 1\n")
    with pytest.raises(ValueError) as exc:
        cs.validate_script_path(str(p), {".py"})
    assert "must be one of" in str(exc.value)


def test_validate_script_path_normalizes_dotdot(tmp_path):
    # A path with a .. segment resolves before the suffix is checked.
    sub = tmp_path / "sub"
    sub.mkdir()
    p = tmp_path / "main.py"
    p.write_text("x = 1\n")
    tricky = str(sub / ".." / "main.py")
    real = cs.validate_script_path(tricky, {".py"})
    assert ".." not in real
    assert real == os.path.realpath(str(p))


def test_validate_script_path_supports_multiple_suffixes(tmp_path):
    p = tmp_path / "part.cq"
    p.write_text("x = 1\n")
    assert cs.validate_script_path(str(p), {".py", ".cq"}).endswith(".cq")


# ── an end-to-end sandbox smoke: a script cannot import os or open files ──────
def test_sandboxed_exec_blocks_os_import():
    b = cs.build_sandbox_builtins("Test")
    g = {"__builtins__": b}
    with pytest.raises(ImportError):
        exec("import os", g)  # noqa: S102 — the whole point is that this fails


def test_sandboxed_exec_has_no_open():
    b = cs.build_sandbox_builtins("Test")
    g = {"__builtins__": b}
    with pytest.raises(NameError):
        exec("open('/etc/passwd')", g)  # noqa: S102 — open is not whitelisted
