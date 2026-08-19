"""Suspender Clip — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The clasp clip of suspenders/braces and mitten-clips — the rigid hard good the Fashion
Cabinet `suspender-clip` notion places and bridges to here for its geometry. A slotted body
carries the webbing at the top; a gripping jaw at the bottom pinches the trouser waistband.
Printed rigid (a print-in-place living-hinge jaw is a variant) it stands in for the metal
clip.

Modes (dispatched via `target_part`):
  * "clip"  — the full body with the webbing slot + gripping jaw plate.
  * "plate" — just the flat body plate (no jaw teeth).

Geometry: a flat plate with a webbing slot cut near the top and a toothed lower edge (a
row of shallow notches) for grip. Straight box cuts only → fast, watertight.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `webbing`).
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
webbing   = float(PARAM(lambda: webbing,   25.0))    # suspender-webbing width (mm)
body_h    = float(PARAM(lambda: body_h,    45.0))    # clip body height (mm)
plate_t   = float(PARAM(lambda: plate_t,   3.0))     # plate thickness (mm)
teeth     = int(  PARAM(lambda: teeth,     5))       # gripping teeth along the jaw
slot_gap  = float(PARAM(lambda: slot_gap,  3.0))     # webbing-slot bar width (mm)

target_part = str(PARAM(lambda: target_part, "clip"))  # clip|plate

# ── Safe clamps ──────────────────────────────────────────────────────────────
webbing  = max(10.0, min(webbing, 50.0))
body_h   = max(25.0, min(body_h, 90.0))
plate_t  = max(2.0, min(plate_t, 6.0))
teeth    = max(2, min(teeth, 12))
slot_gap = max(2.0, min(slot_gap, 8.0))

body_w = webbing + 8.0


def build_plate(with_teeth):
    """A flat plate; when with_teeth, a webbing slot near the top and grip notches along
    the bottom edge."""
    plate = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, plate_t / 2.0))
        .rect(body_w, body_h)
        .extrude(plate_t)
    )
    try:
        plate = plate.edges("|Z").fillet(2.0)
    except Exception:
        pass
    if not with_teeth:
        return plate
    # Webbing slot near the top: two slots leaving a central bar.
    top_y = body_h / 2.0 - 8.0
    for sy in (top_y, top_y - (slot_gap + 4.0)):
        slot = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, sy, plate_t / 2.0))
            .box(webbing, 3.5, plate_t + 2.0)
        )
        plate = plate.cut(slot)
    # Grip teeth: shallow notches cut into the bottom edge.
    tooth_pitch = webbing / teeth
    for i in range(teeth):
        x = -webbing / 2.0 + (i + 0.5) * tooth_pitch
        notch = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(x, -(body_h / 2.0), plate_t / 2.0))
            .box(tooth_pitch * 0.4, 4.0, plate_t + 2.0)
        )
        plate = plate.cut(notch)
    return plate


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "plate":
    result = build_plate(with_teeth=False)
else:
    result = build_plate(with_teeth=True)
