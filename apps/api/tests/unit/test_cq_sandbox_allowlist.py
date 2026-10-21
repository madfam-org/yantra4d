"""Tests for Yantra4D's CadQuery import allowlist (defence in depth).

The shared commons_sandbox core enforces a denylist; this runner-layer allowlist
tightens it so only known-safe packages (and sibling cartridges on curated roots)
may be imported. These tests pin that an import outside the allowlist is refused —
including the file-I/O modules the denylist did not name — while the modules a real
commons cartridge needs are admitted.

The allowlist is NOT the security boundary: the subprocess with a minimal env, a
non-dumpable parent and OS isolation is. Introspection escapes that need no import
are documented here but not asserted as blocked, because the import policy cannot
and does not stop them.
"""

import pytest

from services.engine.cq_sandbox import (
    ALLOWED_IMPORTS,
    build_cq_sandbox_builtins,
    make_allowlist_import,
)


def _exec(src, roots=frozenset()):
    g = {"__builtins__": build_cq_sandbox_builtins("CadQuery scripts", roots)}
    exec(src, g)  # noqa: S102 — exercising the sandbox is the point
    return g


# ── file / IO / codegen modules the denylist did NOT name are refused ──────────
# These are exactly the modules the finding showed the denylist missed (io, codecs,
# …) plus the other file/archive/introspection modules a cartridge has no need for.
@pytest.mark.parametrize("module", [
    "io", "codecs", "builtins", "tempfile", "glob", "fileinput",
    "zipfile", "tarfile", "gzip", "bz2", "lzma", "fnmatch", "linecache",
    "sqlite3", "mmap", "fcntl", "secrets", "webbrowser",
])
def test_filelike_modules_are_refused(module):
    with pytest.raises(ImportError, match="is not allowed"):
        _exec(f"import {module}")


def test_core_denylist_modules_still_refused():
    for module in ("os", "sys", "subprocess", "socket", "ctypes", "pickle", "importlib"):
        with pytest.raises(ImportError, match="is not allowed"):
            _exec(f"import {module}")


def test_submodule_refused_by_top_package():
    with pytest.raises(ImportError, match="is not allowed"):
        _exec("import os.path")
    with pytest.raises(ImportError, match="is not allowed"):
        _exec("from urllib import request")


# ── the modules real commons cartridges need ARE admitted ──────────────────────
@pytest.mark.parametrize("module", [
    "math", "json", "argparse", "pathlib", "re", "itertools", "functools",
    "collections", "dataclasses", "enum", "typing",
])
def test_allowed_modules_import(module):
    _exec(f"import {module}")


def test_cadquery_and_ocp_are_on_the_allowlist():
    # The kernel and its binding are named explicitly.
    assert "cadquery" in ALLOWED_IMPORTS
    assert "OCP" in ALLOWED_IMPORTS


# ── sibling cartridge imports resolve only against curated roots ───────────────
def test_sibling_cartridge_on_curated_root_is_allowed(tmp_path, monkeypatch):
    import sys

    (tmp_path / "shared_lib").mkdir()
    (tmp_path / "shared_lib" / "__init__.py").write_text("VALUE = 1\n")
    # The curated root is on sys.path in production (the engine puts it on the
    # child's PYTHONPATH); mirror that here so the admitted import can resolve.
    monkeypatch.syspath_prepend(str(tmp_path))
    guard = make_allowlist_import("CadQuery scripts", frozenset({str(tmp_path)}))
    # top package exists on the curated root → admitted (delegates to real import)
    mod = guard("shared_lib")
    assert mod is not None
    assert mod.VALUE == 1
    sys.modules.pop("shared_lib", None)


def test_cartridge_name_shadowing_a_blocked_module_is_still_refused(tmp_path):
    # A user directory named like a blocked module must not smuggle it in.
    (tmp_path / "os").mkdir()
    (tmp_path / "os" / "__init__.py").write_text("x = 1\n")
    guard = make_allowlist_import("CadQuery scripts", frozenset({str(tmp_path)}))
    with pytest.raises(ImportError):
        guard("os")


def test_unknown_name_not_on_any_curated_root_is_refused(tmp_path):
    guard = make_allowlist_import("CadQuery scripts", frozenset({str(tmp_path)}))
    with pytest.raises(ImportError, match="is not allowed"):
        guard("requests")


# ── no capability-granting builtins (inherited from the core) ──────────────────
def test_no_open_eval_exec():
    b = build_cq_sandbox_builtins("CadQuery scripts")
    for forbidden in ("open", "eval", "exec", "compile", "getattr", "globals", "vars"):
        assert forbidden not in b


# ── documented introspection escapes the import policy does NOT stop ───────────
def test_documented_introspection_escape_is_not_claimed_blocked():
    """Record, do not assert-block: code can reach interpreter internals without
    importing anything, so the import allowlist does not stop this. The boundary
    is the subprocess env, the non-dumpable parent and OS isolation — not this
    policy. Asserting a block here would be a false guarantee.
    """
    g = {"__builtins__": build_cq_sandbox_builtins("CadQuery scripts")}
    # type(()).__base__.__subclasses__() is reachable with only safe builtins and
    # no import. We confirm it is reachable (so the test documents the real
    # residual), using a non-empty subclass list as the observable proof.
    exec(  # noqa: S102
        "reached = len(type(()).__base__.__subclasses__()) > 0",
        g,
    )
    assert g["reached"] is True
