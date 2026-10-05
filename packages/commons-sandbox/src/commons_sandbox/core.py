"""The restricted-execution security core shared by MADFAM hyperobject runners.

Dependency-free and kernel-agnostic. See the package docstring for the threat model.
Anything security-relevant lives here so it is authored, reviewed, and fixed once.
"""

from __future__ import annotations

import builtins as _builtins
import os
import platform
from collections.abc import Callable, Iterable, Mapping


# ── restricted reflection builtins ───────────────────────────────────────────
def safe_type(obj, *args):
    """Restricted type() — one-argument only; blocks the 3-argument metaclass form
    that a cartridge could use to synthesize a class with a custom metaclass."""
    if args:
        raise TypeError("type() with 3 arguments is not allowed in sandboxed scripts")
    return _builtins.type(obj)


def safe_isinstance(obj, classinfo):
    """Restricted isinstance() — no metaclass traversal exposure."""
    return _builtins.isinstance(obj, classinfo)


def safe_issubclass(cls, classinfo):
    """Restricted issubclass() — no class-hierarchy exposure."""
    return _builtins.issubclass(cls, classinfo)


# ── the safe-builtins whitelist ──────────────────────────────────────────────
# Only pure-computation constructors, iteration/number/string helpers, and
# exception classes. No open/eval/exec/compile/__import__/getattr/globals/vars —
# those are the capability-granting builtins and are deliberately absent.
# NameError is included so the commons' PARAM idiom (probe an injected global,
# catch NameError when absent) can catch precisely rather than broadly; exception
# classes grant no capability, so exposing them does not widen the sandbox.
SAFE_BUILTINS: dict[str, object] = {
    # Core types and constructors
    "True": True, "False": False, "None": None,
    "int": int, "float": float, "str": str, "bool": bool,
    "list": list, "dict": dict, "tuple": tuple, "set": set, "frozenset": frozenset,
    "bytes": bytes, "bytearray": bytearray, "complex": complex,
    # Iteration and ranges
    "range": range, "enumerate": enumerate, "zip": zip, "map": map, "filter": filter,
    "reversed": reversed, "sorted": sorted, "iter": iter, "next": next,
    # Math and numeric
    "abs": abs, "round": round, "min": min, "max": max, "sum": sum, "pow": pow,
    "divmod": divmod,
    # Length and membership
    "len": len, "any": any, "all": all,
    "isinstance": safe_isinstance, "issubclass": safe_issubclass,
    "type": safe_type, "id": id, "hash": hash,
    # String and repr
    "repr": repr, "format": format, "chr": chr, "ord": ord,
    "print": print,
    # Exceptions (scripts may catch/raise)
    "Exception": Exception, "ValueError": ValueError, "TypeError": TypeError,
    "NameError": NameError,
    "RuntimeError": RuntimeError, "KeyError": KeyError, "IndexError": IndexError,
    "AttributeError": AttributeError, "StopIteration": StopIteration,
    "ZeroDivisionError": ZeroDivisionError,
}

# Modules a cartridge must never import — file I/O, process/network access, code
# generation, and serialization that can execute code.
BLOCKED_MODULES: frozenset[str] = frozenset({
    "os", "sys", "subprocess", "shutil", "socket", "http", "urllib",
    "importlib", "ctypes", "signal", "multiprocessing", "threading",
    "pickle", "shelve", "code", "codeop", "compile", "compileall",
})


def make_restricted_import(product_label: str = "sandboxed") -> Callable:
    """Return an ``__import__`` replacement that blocks BLOCKED_MODULES.

    ``product_label`` only shapes the error message (e.g. "Fashion Cabinet
    cartridges", "CadQuery scripts"); it changes no policy."""

    def _restricted_import(name, globals=None, locals=None, fromlist=(), level=0):
        # A sandboxed script runs as ``__main__`` with no package, so it has no
        # legitimate relative import. Refuse them: a relative import resolves
        # against the caller's ``__package__``, not against ``name``, so the
        # top-package check below could not see what it actually loads.
        if level:
            raise ImportError(
                f"Relative import is not allowed in {product_label}"
            )
        top = name.split(".")[0]
        if top in BLOCKED_MODULES:
            raise ImportError(f"Import of '{name}' is not allowed in {product_label}")
        # Delegate to the real importer for everything else. __builtins__ can be a
        # module or a dict depending on the caller's frame.
        real = __builtins__["__import__"] if isinstance(__builtins__, dict) \
            else __builtins__.__import__
        return real(name, globals, locals, fromlist, level)

    return _restricted_import


def make_allowlist_import(
    product_label: str,
    allowed_imports: Iterable[str],
    allow: Callable[[str], bool] | None = None,
) -> Callable:
    """Return an ``__import__`` replacement that admits only named top-level packages.

    An import is admitted when its top-level package is in ``allowed_imports``, or
    when ``allow(top)`` returns true (a runner's own rule, e.g. a sibling cartridge
    on a curated root). Everything else is refused. An admitted import still goes
    through ``make_restricted_import``, so ``BLOCKED_MODULES`` always wins and a
    relative import is refused, whatever a caller lists.

    A runner owns its list (it is kernel-specific); this function owns the
    mechanism, so both runners enforce an allowlist the same way."""
    allowed = frozenset(allowed_imports)
    restricted = make_restricted_import(product_label)

    def _allowlist_import(name, globals=None, locals=None, fromlist=(), level=0):
        if level:
            # The restricted import refuses it with the shared message.
            return restricted(name, globals, locals, fromlist, level)
        top = name.split(".")[0]
        if top not in BLOCKED_MODULES and (
            top in allowed or (allow is not None and allow(top))
        ):
            return restricted(name, globals, locals, fromlist, level)
        raise ImportError(f"Import of '{name}' is not allowed in {product_label}")

    return _allowlist_import


def build_sandbox_builtins(
    product_label: str = "sandboxed",
    allowed_imports: Iterable[str] | None = None,
    allow: Callable[[str], bool] | None = None,
) -> dict:
    """A fresh copy of SAFE_BUILTINS with a guarded ``__import__`` installed —
    ready to drop into an ``exec`` globals as ``__builtins__``. A copy, so a caller
    (or a script) mutating it cannot poison the shared whitelist.

    With ``allowed_imports`` the guard is ``make_allowlist_import`` (only the named
    packages, plus whatever ``allow`` admits); without it, the denylist guard
    ``make_restricted_import``. Runners should pass an allowlist."""
    b = dict(SAFE_BUILTINS)
    if allowed_imports is None:
        b["__import__"] = make_restricted_import(product_label)
    else:
        b["__import__"] = make_allowlist_import(product_label, allowed_imports, allow)
    return b


# ── the runner subprocess environment ────────────────────────────────────────
# What a runner subprocess may inherit from its parent, by exact name: the
# executable search path, locale and time zone, the temp dir, the dynamic linker's
# search path (a shared-library Python build cannot start without it) and the
# interpreter's behaviour flags. ``LD_PRELOAD`` and ``PYTHONHOME`` are deliberately
# not here, and neither is ``PYTHONPATH``: a runner sets the import path it needs.
CHILD_ENV_NAMES: frozenset[str] = frozenset({
    "PATH", "LANG", "LC_ALL", "LC_CTYPE", "TZ", "TMPDIR",
    "LD_LIBRARY_PATH",
    "PYTHONUNBUFFERED", "PYTHONHASHSEED", "PYTHONDONTWRITEBYTECODE",
})


def minimal_child_env(
    parent_env: Mapping[str, str],
    extra_names: Iterable[str] = (),
    extra_prefixes: Iterable[str] = (),
) -> dict[str, str]:
    """The subset of ``parent_env`` a runner subprocess may inherit.

    Built from an allowlist, never by copying and deleting: ``CHILD_ENV_NAMES``,
    plus the runner's ``extra_names`` (exact) and ``extra_prefixes`` (e.g. a
    kernel's own settings). Application configuration and credentials are
    therefore never in the child's ``os.environ``, whatever the parent holds."""
    names = CHILD_ENV_NAMES | frozenset(extra_names)
    prefixes = tuple(extra_prefixes)
    return {
        key: value for key, value in parent_env.items()
        if key in names or (prefixes and key.startswith(prefixes))
    }


# <linux/prctl.h>
_PR_GET_DUMPABLE = 3
_PR_SET_DUMPABLE = 4


def set_process_nondumpable() -> bool:
    """Mark the calling process non-dumpable (Linux ``prctl(PR_SET_DUMPABLE, 0)``).

    A runner's subprocess shares its parent's UID; a non-dumpable parent's
    ``/proc/<pid>/environ`` and ``/proc/<pid>/mem`` are not readable by it. Call it
    in every process that starts runner subprocesses. Returns True only when the
    flag is confirmed set. A no-op returning False off Linux, and it never raises:
    a hardening step must not stop the process it protects."""
    if platform.system() != "Linux":
        return False
    try:
        import ctypes  # local: only the parent process ever needs it

        libc = ctypes.CDLL(None, use_errno=True)
        if libc.prctl(_PR_SET_DUMPABLE, 0, 0, 0, 0) != 0:
            return False
        return libc.prctl(_PR_GET_DUMPABLE, 0, 0, 0, 0) == 0
    except Exception:  # noqa: BLE001 - never raise from a hardening step
        return False


def validate_script_path(script_path: str, allowed_suffixes: set[str]) -> str:
    """Resolve ``script_path`` to a real path and require an allowed suffix.

    Uses ``os.path.realpath`` so a path with symlinks or ``..`` segments is
    normalized before its suffix is checked (a hardening one runner had dropped).
    Returns the real path; raises ValueError on a disallowed suffix."""
    real = os.path.realpath(script_path)
    if not any(real.endswith(suffix) for suffix in allowed_suffixes):
        allowed = " | ".join(sorted(allowed_suffixes))
        raise ValueError(f"Script must be one of [{allowed}], got: {script_path}")
    return real


def read_script(script_path: str) -> str:
    """Read a cartridge script's text (small files; utf-8)."""
    with open(script_path, encoding="utf-8") as f:
        return f.read()
