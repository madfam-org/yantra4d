"""commons-sandbox — the shared restricted-execution core for MADFAM hyperobject runners.

Fashion Cabinet's ``fc_runner`` and Yantra4D's ``cq_runner`` execute untrusted
cartridge scripts (``main.py`` authored by third parties) in a restricted sandbox:
a whitelist of safe builtins, an import guard (an allowlist a runner names, over a
blocklist of dangerous modules, with relative imports refused), a validated script
path, a minimal subprocess environment, and a non-dumpable parent. That security
core was byte-identical across the two runners and had begun to drift (one repo kept
a real-path hardening the other dropped). This package is the single authored source
of that core, so a sandbox-hardening fix is made once and cannot silently diverge.

It is deliberately DEPENDENCY-FREE and kernel-agnostic: it knows nothing about ``fc``
or ``cq``. Each runner supplies its own injected namespace, result detection, and
export path, and calls this package for the security core:

    from commons_sandbox import (
        build_sandbox_builtins, minimal_child_env, read_script,
        set_process_nondumpable, validate_script_path,
    )

    # in the parent that starts the runner subprocess:
    set_process_nondumpable()
    subprocess.run(cmd, env=minimal_child_env(os.environ))

    # in the runner:
    validate_script_path(script_path, {".py"})          # realpath-checked
    builtins_ = build_sandbox_builtins("Fashion Cabinet", allowed_imports={"fc", "math"})
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
    CHILD_ENV_NAMES,
    SAFE_BUILTINS,
    build_sandbox_builtins,
    make_allowlist_import,
    make_restricted_import,
    minimal_child_env,
    read_script,
    safe_isinstance,
    safe_issubclass,
    safe_type,
    set_process_nondumpable,
    validate_script_path,
)

__all__ = [
    "SAFE_BUILTINS",
    "BLOCKED_MODULES",
    "safe_type",
    "safe_isinstance",
    "safe_issubclass",
    "make_restricted_import",
    "make_allowlist_import",
    "build_sandbox_builtins",
    "CHILD_ENV_NAMES",
    "minimal_child_env",
    "set_process_nondumpable",
    "validate_script_path",
    "read_script",
    "__version__",
]

__version__ = "1.1.0"
