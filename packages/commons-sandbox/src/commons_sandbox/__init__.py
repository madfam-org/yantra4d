"""commons-sandbox — the shared restricted-execution core for MADFAM hyperobject runners.

Fashion Cabinet's ``fc_runner`` and Yantra4D's ``cq_runner`` execute untrusted
cartridge scripts (``main.py`` authored by third parties) in a restricted sandbox:
a whitelist of safe builtins, a blocklist of dangerous modules, an import guard, and
a validated script path. That security core was byte-identical across the two runners
and had begun to drift (one repo kept a real-path hardening the other dropped). This
package is the single authored source of that core, so a sandbox-hardening fix is
made once and cannot silently diverge.

It is deliberately DEPENDENCY-FREE and kernel-agnostic: it knows nothing about ``fc``
or ``cq``. Each runner supplies its own injected namespace, result detection, and
export path, and calls this package for the security core:

    from commons_sandbox import (
        SAFE_BUILTINS, make_restricted_import, build_sandbox_builtins,
        validate_script_path, read_script,
    )

    validate_script_path(script_path, {".py"})          # realpath-checked
    builtins_ = build_sandbox_builtins("Fashion Cabinet")
    exec_globals = {"__builtins__": builtins_, "fc": fc, "math": math,
                    "__file__": script_path, "__name__": "__main__"}
    exec(read_script(script_path), exec_globals)         # sandboxed

The threat model is defense-in-depth, NOT a security boundary on its own: it raises
the bar against casual file/network/code-exec inside a cartridge, but the runner is
still expected to run as a killable subprocess with OS-level limits. Exposing
exception classes and pure-computation builtins grants no capability; the blocklist +
import guard are what matter.
"""

from __future__ import annotations

from .core import (
    BLOCKED_MODULES,
    SAFE_BUILTINS,
    build_sandbox_builtins,
    make_restricted_import,
    read_script,
    safe_isinstance,
    safe_issubclass,
    safe_type,
    validate_script_path,
)

__all__ = [
    "SAFE_BUILTINS",
    "BLOCKED_MODULES",
    "safe_type",
    "safe_isinstance",
    "safe_issubclass",
    "make_restricted_import",
    "build_sandbox_builtins",
    "validate_script_path",
    "read_script",
    "__version__",
]

__version__ = "1.0.0"
