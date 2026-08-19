"""Collar Stay — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The collar stay — the thin tapered blade slipped into a shirt-collar point to keep it
crisp — the rigid hard good the Fashion Cabinet `collar-stay` notion places and bridges to
here for its geometry. Printed in a springy filament it stands in for the metal or plastic
stay.

Modes (dispatched via `target_part`):
  * "stay"  — a single tapered stay.
  * "pair"  — a mirrored pair (left + right collar points).

Geometry: an extruded tapered blade (rounded rectangle tapering to a rounded point);
straight line-segment profile with a fillet, no arcs. Watertight.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `stay_len`).
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
stay_len  = float(PARAM(lambda: stay_len,  65.0))    # collar-point length (mm)
base_w    = float(PARAM(lambda: base_w,    12.0))    # width at the base (mm)
tip_w     = float(PARAM(lambda: tip_w,     5.0))     # width at the point (mm)
stay_t    = float(PARAM(lambda: stay_t,    1.2))     # blade thickness (mm)

target_part = str(PARAM(lambda: target_part, "stay"))  # stay|pair

# ── Safe clamps ──────────────────────────────────────────────────────────────
stay_len = max(35.0, min(stay_len, 120.0))
base_w   = max(6.0, min(base_w, 25.0))
tip_w    = max(2.0, min(tip_w, base_w - 1.0))
stay_t   = max(0.6, min(stay_t, 4.0))


def build_stay():
    """A tapered blade from base (y=0, base_w) to point (y=stay_len, tip_w), extruded
    stay_t thick, with the vertical edges filleted for a smooth stay."""
    blade = (
        cq.Workplane("XY")
        .polyline([(-base_w / 2.0, 0.0), (base_w / 2.0, 0.0),
                   (tip_w / 2.0, stay_len), (-tip_w / 2.0, stay_len)])
        .close()
        .extrude(stay_t)
    )
    try:
        blade = blade.edges("|Z").fillet(min(tip_w * 0.45, base_w * 0.2))
    except Exception:
        pass
    return blade


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "pair":
    result = build_stay().translate((-base_w, 0, 0)).union(
        build_stay().translate((base_w, 0, 0)))
else:
    result = build_stay()
