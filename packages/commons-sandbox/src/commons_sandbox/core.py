"""The restricted-execution security core shared by MADFAM hyperobject runners.

Dependency-free and kernel-agnostic. See the package docstring for the threat model.
Anything security-relevant lives here so it is authored, reviewed, and fixed once.
"""

from __future__ import annotations

import builtins as _builtins
import os
from collections.abc import Callable


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
        top = name.split(".")[0]
        if top in BLOCKED_MODULES:
            raise ImportError(f"Import of '{name}' is not allowed in {product_label}")
        # Delegate to the real importer for everything else. __builtins__ can be a
        # module or a dict depending on the caller's frame.
        real = __builtins__["__import__"] if isinstance(__builtins__, dict) \
            else __builtins__.__import__
        return real(name, globals, locals, fromlist, level)

    return _restricted_import


def build_sandbox_builtins(product_label: str = "sandboxed") -> dict:
    """A fresh copy of SAFE_BUILTINS with the restricted ``__import__`` installed —
    ready to drop into an ``exec`` globals as ``__builtins__``. A copy, so a caller
    (or a script) mutating it cannot poison the shared whitelist."""
    b = dict(SAFE_BUILTINS)
    b["__import__"] = make_restricted_import(product_label)
    return b


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
