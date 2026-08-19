"""Toggle — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The barrel toggle of duffle coats, drawstrings, and closures — the rigid hard good the
Fashion Cabinet `toggle-closure` notion places and bridges to here for its geometry. A
turned barrel with a transverse cord channel; the cord knots through it and the toggle
passes through a loop to fasten. Printed rigid (wood-look filament optional) it stands in
for the horn/wood toggle.

Modes (dispatched via `target_part`):
  * "toggle" — the barrel toggle.
  * "bar"    — a straight bar toggle variant (same builder, longer + slimmer).

Geometry: a cylinder barrel with rounded ends (fillet) and a transverse bore (a cylinder
cut across it) for the cord. Watertight.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `barrel_len`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq


def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
barrel_len = float(PARAM(lambda: barrel_len, 38.0))  # toggle length (mm)
barrel_dia = float(PARAM(lambda: barrel_dia, 12.0))  # toggle diameter (mm)
cord_dia   = float(PARAM(lambda: cord_dia,   4.0))   # cord-channel diameter (mm)
cords      = int(  PARAM(lambda: cords,      2))     # 1 or 2 cord channels

target_part = str(PARAM(lambda: target_part, "toggle"))  # toggle|bar

# ── Safe clamps ──────────────────────────────────────────────────────────────
barrel_len = max(18.0, min(barrel_len, 80.0))
barrel_dia = max(6.0, min(barrel_dia, 24.0))
cord_dia   = max(1.5, min(cord_dia, barrel_dia - 3.0))
cords      = max(1, min(cords, 2))


def build_toggle(length, dia):
    """A barrel lying along X, rounded ends, with transverse cord bore(s) through Z."""
    barrel = (
        cq.Workplane("YZ")
        .transformed(offset=cq.Vector(0, 0, -length / 2.0))
        .circle(dia / 2.0)
        .extrude(length)
    )
    try:
        barrel = barrel.edges().fillet(min(dia * 0.28, length * 0.2))
    except Exception:
        pass
    # Cord channel(s) bored through Z at 1 or 2 positions along the barrel.
    positions = [0.0] if cords == 1 else [-length * 0.22, length * 0.22]
    for px in positions:
        bore = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(px, 0, 0))
            .circle(cord_dia / 2.0)
            .extrude(dia + 4.0)
            .translate((0, 0, -(dia + 4.0) / 2.0))
        )
        barrel = barrel.cut(bore)
    return barrel


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "bar":
    result = build_toggle(barrel_len * 1.4, barrel_dia * 0.7)
else:
    result = build_toggle(barrel_len, barrel_dia)
