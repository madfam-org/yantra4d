"""Yantra4D's import policy for CadQuery cartridge scripts.

The shared ``commons_sandbox`` core is dependency-free and kernel-agnostic. Its
default import guard is a *denylist* (``BLOCKED_MODULES``); since core 1.1.0 it
also carries the allowlist mechanism (``make_allowlist_import``), and both guards
refuse relative imports. The core is vendored here under a byte-hash lock and is
changed only by re-vendoring, so this module owns only Yantra4D's *policy*: the
list below and the curated-sibling rule. The mechanism is the core's.

A denylist is only as complete as its author's imagination. A CadQuery cartridge
needs a small, knowable set of modules — the kernel, the standard numeric and
serialization helpers, and the cartridge's own sibling cartridges — so the policy
that actually ships to the runner is an *allowlist*: an import whose top-level
package is not named here is refused, regardless of whether the core denylist
happened to list it.

The allowlist was derived by scanning every CadQuery script in the public commons
(``projects/`` and madfam-org/solid-hyperobjects): their only imports are
``cadquery``, ``math``, ``json``, ``argparse``, ``OCP`` (CadQuery's OCCT binding,
used by a few low-level cartridges), and ``pathlib`` (one cartridge resolves a
bundled font relative to ``__file__``). The remaining names below are a modest,
safe-by-construction margin — pure-computation standard-library modules a legitimate
cartridge author might reach for — none of which grants file, process, network, or
code-generation capability on its own.

Sibling cartridge imports (a cartridge importing another cartridge's package by
name) resolve because the cartridge roots are on ``PYTHONPATH`` and the top-level
package name is whatever the sibling directory is called; those are allowed through
the ``_curated_cartridge_import`` predicate rather than being enumerated here.

This remains **defence in depth, not a security boundary.** Python's object graph
lets determined code reach interpreter internals without importing anything, so the
import policy only raises the bar against casual file/network/code-exec in a
cartridge. The boundary is the killable subprocess with a minimal environment, a
non-dumpable parent, OS-level limits, and (in production) network and filesystem
isolation.
"""

from __future__ import annotations

from collections.abc import Callable

from commons_sandbox import BLOCKED_MODULES, build_sandbox_builtins
from commons_sandbox import make_allowlist_import as core_make_allowlist_import

# Top-level package names a CadQuery cartridge may import. Derived from a scan of
# the public commons (see the module docstring). Pure-computation standard-library
# modules only — nothing here grants file, process, network, or code capability on
# its own, and the subprocess boundary is what actually contains a cartridge.
#
# Keep this list minimal: every addition widens what a cartridge may reach, so a
# new entry belongs here only when a real commons cartridge demonstrably needs it.
ALLOWED_IMPORTS: frozenset[str] = frozenset({
    # The kernel and its binding.
    "cadquery",
    "OCP",
    # Numerics and data a cartridge computes with.
    "math",
    "cmath",
    "statistics",
    "fractions",
    "decimal",
    "random",
    "json",
    "re",
    # Iteration / functional helpers.
    "itertools",
    "functools",
    "operator",
    "collections",
    "dataclasses",
    "enum",
    "typing",
    # A cartridge's own argument parsing (several commons cartridges use it).
    "argparse",
    # Path handling relative to the cartridge's own __file__ (bundled fonts).
    "pathlib",
    # Future-import machinery is not a real module import at runtime, but a
    # cartridge may carry ``from __future__ import ...``.
    "__future__",
})


def _is_curated_cartridge(top: str, curated_roots: frozenset[str]) -> bool:
    """Whether *top* names a sibling cartridge package on a curated root.

    A cartridge importing another cartridge by its directory name is a supported
    commons pattern. We allow it only when a directory of that exact name exists
    on one of the curated cartridge roots — never the user-projects root, whose
    directory names are chosen by users (see ``curated_project_roots``). The
    import is still subject to the core denylist, so a cartridge directory named
    like a blocked module cannot smuggle one in.
    """
    import os

    if top in BLOCKED_MODULES:
        return False
    for root in curated_roots:
        candidate = os.path.join(root, top)
        if os.path.isdir(candidate) or os.path.isfile(candidate + ".py"):
            return True
    return False


def make_allowlist_import(
    product_label: str,
    curated_roots: frozenset[str] = frozenset(),
) -> Callable:
    """An ``__import__`` replacement that admits only known-safe packages.

    An import is admitted when its top-level package is in ``ALLOWED_IMPORTS`` or
    names a cartridge on a curated root; everything else is refused. The guard is
    the shared core's ``make_allowlist_import``, so ``BLOCKED_MODULES`` always wins
    and a relative import is refused: a cartridge script runs as ``__main__`` with
    no package, so it has no legitimate one.
    """
    return core_make_allowlist_import(
        product_label,
        ALLOWED_IMPORTS,
        allow=lambda top: _is_curated_cartridge(top, curated_roots),
    )


def build_cq_sandbox_builtins(
    product_label: str = "CadQuery scripts",
    curated_roots: frozenset[str] = frozenset(),
) -> dict:
    """Sandbox builtins for CadQuery scripts with the allowlist import installed.

    A drop-in replacement for ``commons_sandbox.build_sandbox_builtins`` that
    swaps the core's denylist ``__import__`` for Yantra4D's allowlist one. The
    safe-builtins whitelist (no ``open``/``eval``/``exec``/…) is the core's,
    unchanged.
    """
    builtins_ = build_sandbox_builtins(product_label)
    builtins_["__import__"] = make_allowlist_import(product_label, curated_roots)
    return builtins_
