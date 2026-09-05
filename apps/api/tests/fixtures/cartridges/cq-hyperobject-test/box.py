"""Parametric Box — Yantra4D CadQuery engine test fixture.

A single watertight box. One mode, one part (`box`), so the platform always
injects target_part == "box"; the script has no dispatch to make and simply
builds the one body.

Sandbox contract (apps/api/services/engine/cq_runner.py): parameters arrive as
BARE globals in the exec namespace. `globals()` is NOT exposed by the sandbox
builtins, so parameters are read through PARAM(), whose `except Exception`
catches the NameError raised for an unbound param name.
"""

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present and non-None, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
width = float(PARAM(lambda: width, 10.0))    # box X extent (mm)
length = float(PARAM(lambda: length, 10.0))  # box Y extent (mm)
height = float(PARAM(lambda: height, 10.0))  # box Z extent (mm)

# ── Build ────────────────────────────────────────────────────────────────────
result = cq.Workplane("XY").box(width, length, height)
