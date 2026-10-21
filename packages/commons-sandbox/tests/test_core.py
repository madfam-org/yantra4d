"""Tests for the shared sandbox security core.

This is security-critical code with ONE authored source, so its guarantees are
tested here directly: the whitelist admits only safe builtins, the blocklist +
import guard actually stop dangerous imports, the reflection builtins are
restricted, and the path validator normalizes real paths.
"""

import os
import subprocess
import sys

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


# ── relative imports are refused ─────────────────────────────────────────────
@pytest.mark.parametrize("builder", [
    lambda: cs.build_sandbox_builtins("Test"),
    lambda: cs.build_sandbox_builtins("Test", allowed_imports={"math"}),
], ids=["denylist", "allowlist"])
def test_a_relative_import_is_refused_whatever_the_script_sets(builder):
    # A sandboxed script runs as __main__ with no package; a relative import
    # resolves against the script's own __package__, which it controls.
    for package in ("os", "math", "commons_sandbox"):
        g = {"__builtins__": builder(), "__name__": "__main__"}
        with pytest.raises(ImportError) as exc:
            exec(f"__package__ = {package!r}\nfrom . import x", g)  # noqa: S102
        assert "Relative import is not allowed in Test" in str(exc.value)


def test_the_guards_refuse_a_nonzero_level_directly():
    for guard in (cs.make_restricted_import("Test"),
                  cs.make_allowlist_import("Test", {"math"})):
        with pytest.raises(ImportError):
            guard("", {"__package__": "os"}, None, ("getcwd",), 1)
        with pytest.raises(ImportError):
            guard("path", {"__package__": "os"}, None, (), 2)


# ── the allowlist guard ──────────────────────────────────────────────────────
def test_allowlist_admits_only_named_packages():
    guard = cs.make_allowlist_import("Test scripts", {"math", "json"})
    assert guard("math") is not None
    assert guard("json.decoder") is not None          # by top-level package
    for name in ("io", "codecs", "pathlib", "random", "os", "os.path"):
        with pytest.raises(ImportError) as exc:
            guard(name)
        assert f"Import of '{name}' is not allowed in Test scripts" in str(exc.value)


def test_allowlist_never_admits_a_blocked_module():
    guard = cs.make_allowlist_import("Test", {"os", "subprocess", "math"},
                                     allow=lambda top: True)
    for name in ("os", "subprocess", "socket"):
        with pytest.raises(ImportError):
            guard(name)
    assert guard("math") is not None


def test_allowlist_predicate_extends_the_list():
    seen = []

    def allow(top):
        seen.append(top)
        return top == "json"

    guard = cs.make_allowlist_import("Test", {"math"}, allow=allow)
    assert guard("json") is not None
    with pytest.raises(ImportError):
        guard("re")
    assert seen == ["json", "re"]


def test_build_sandbox_builtins_installs_the_allowlist_when_given():
    b = cs.build_sandbox_builtins("Test", allowed_imports={"math"})
    g = {"__builtins__": b}
    exec("import math\nr = math.sqrt(4)", g)  # noqa: S102
    assert g["r"] == 2.0
    with pytest.raises(ImportError):
        exec("import io", {"__builtins__": b})  # noqa: S102
    # The default stays the denylist guard (io is not on the blocklist).
    exec("import io", {"__builtins__": cs.build_sandbox_builtins("Test")})  # noqa: S102


# ── the subprocess environment ───────────────────────────────────────────────
def test_minimal_child_env_keeps_only_allowlisted_names():
    parent = {
        "PATH": "/usr/bin", "LANG": "C.UTF-8", "TMPDIR": "/tmp",
        "LD_LIBRARY_PATH": "/opt/lib", "PYTHONUNBUFFERED": "1",
        "SOME_CLIENT_SECRET": "x", "SOME_API_KEY": "x", "AWS_ACCESS_KEY_ID": "x",
        "LD_PRELOAD": "/x.so", "PYTHONHOME": "/x", "PYTHONPATH": "/app",
        "FC_ROOT": "/app", "KERNEL_FONT_DIR": "/f",
    }
    child = cs.minimal_child_env(parent)
    assert child == {"PATH": "/usr/bin", "LANG": "C.UTF-8", "TMPDIR": "/tmp",
                     "LD_LIBRARY_PATH": "/opt/lib", "PYTHONUNBUFFERED": "1"}
    child = cs.minimal_child_env(parent, extra_names={"FC_ROOT"},
                                 extra_prefixes=("KERNEL_",))
    assert child["FC_ROOT"] == "/app" and child["KERNEL_FONT_DIR"] == "/f"
    for name in ("SOME_CLIENT_SECRET", "SOME_API_KEY", "AWS_ACCESS_KEY_ID",
                 "LD_PRELOAD", "PYTHONHOME", "PYTHONPATH"):
        assert name not in child


def test_child_env_names_exclude_loader_and_interpreter_overrides():
    for name in ("LD_PRELOAD", "PYTHONHOME", "PYTHONPATH", "PYTHONSTARTUP"):
        assert name not in cs.CHILD_ENV_NAMES


# ── the non-dumpable parent ──────────────────────────────────────────────────
def test_set_process_nondumpable_is_a_safe_noop_off_linux(monkeypatch):
    import commons_sandbox.core as core

    monkeypatch.setattr(core.platform, "system", lambda: "Darwin")
    assert cs.set_process_nondumpable() is False


@pytest.mark.skipif(sys.platform != "linux", reason="prctl is Linux-only")
def test_set_process_nondumpable_hides_the_parent_environ_from_a_child():
    # In a throwaway process, so the test runner itself is left dumpable.
    code = (
        "import os, subprocess, sys\n"
        "import commons_sandbox as cs\n"
        "assert cs.set_process_nondumpable() is True\n"
        "child = ('import os, sys\\n'\n"
        "         'try:\\n'\n"
        "         '    open(f\"/proc/{os.getppid()}/environ\", \"rb\").read()\\n'\n"
        "         '    print(\"READ\")\\n'\n"
        "         'except PermissionError:\\n'\n"
        "         '    print(\"DENIED\")\\n')\n"
        "out = subprocess.run([sys.executable, '-c', child], capture_output=True,\n"
        "                     text=True, check=True).stdout.strip()\n"
        "print(out)\n"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                         check=True).stdout.strip()
    assert out == "DENIED"
