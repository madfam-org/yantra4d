# madfam-commons-sandbox (`commons_sandbox`)

The shared restricted-execution core for MADFAM hyperobject cartridge runners.

Both Fashion Cabinet (`fc_runner`) and Yantra4D (`cq_runner`) execute untrusted
third-party cartridge scripts (`main.py`) in a sandbox: a whitelist of safe
builtins, a blocklist of dangerous modules, an import guard, and a validated script
path. That security core was **byte-identical across the two runners and had begun
to drift** (one repo kept a real-path hardening the other had dropped). This package
is the single authored source of that core, so a sandbox-hardening fix is made once
and cannot silently diverge.

It is **dependency-free and kernel-agnostic** — it knows nothing about `fc` or `cq`.
Each runner supplies its own injected namespace, result detection, and export path.

## Use

```python
from commons_sandbox import (
    build_sandbox_builtins, read_script, validate_script_path,
)

validate_script_path(script_path, {".py"})          # realpath-checked, suffix-gated
safe_builtins = build_sandbox_builtins("Fashion Cabinet cartridges")
exec_globals = {
    "__builtins__": safe_builtins,
    "fc": fc, "math": math,                          # the runner's own namespace
    "__file__": script_path, "__name__": "__main__",
}
exec(read_script(script_path), exec_globals)         # sandboxed
```

## What it exposes

| Name | Purpose |
|---|---|
| `SAFE_BUILTINS` | the whitelist dict (no `open`/`eval`/`exec`/`compile`/`__import__`/`getattr`/`globals`) |
| `BLOCKED_MODULES` | the frozenset a cartridge may never import (`os`, `subprocess`, `socket`, `ctypes`, `pickle`, …) |
| `make_restricted_import(label)` | an `__import__` replacement enforcing the blocklist (top-package match) |
| `build_sandbox_builtins(label)` | a fresh `SAFE_BUILTINS` copy with the restricted import installed |
| `validate_script_path(path, suffixes)` | resolves the real path (normalizing `..`/symlinks) and gates the suffix |
| `read_script(path)` | reads a cartridge script (utf-8) |
| `safe_type` / `safe_isinstance` / `safe_issubclass` | reflection builtins that block the 3-arg metaclass form |

## Threat model

Defense-in-depth, **not** a security boundary on its own. It raises the bar against
casual file/network/code-exec inside a cartridge, but the runner is still expected to
run as a **killable subprocess with OS-level limits** (CPU/memory/wall-clock). Exposing
exception classes and pure-computation builtins grants no capability; the blocklist +
import guard are what matter.

## Distribution

Authored here as the canonical source. Fashion Cabinet installs and imports it
directly (`pip install -e packages/commons-sandbox`). Yantra4D consumes the same core
— see `internal-devops` for the cross-repo plan; until a shared MADFAM Python registry
exists, the yantra4d side vendors this package with a byte-equality CI guard, then
switches to a plain `pip` dependency once the registry is up.

Platform code: AGPL-3.0.
