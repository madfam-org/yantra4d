"""
Key / Zipper Grip Aid — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Grip enlargers for the small, hard-to-turn objects of daily life: keys, zipper
pulls, and small tabs. Each part captures a thin flat tab (a key bow, a zip
slider's pull-hole, or a button/cord toggle) in a pocket and gives it a large,
easy-to-hold body so a user with limited pinch strength, arthritis, tremor, or
one-handed use can turn, pull, or grasp it. Sized to the standard tabs it fits.

  * "key_turner" — a broad wing/lever whose slot captures a key's bow, turning a
                   hard key with the whole hand (target_part == "key_turner").
  * "zip_pull"   — a teardrop pull with a small bar-slot that hooks a zipper
                   slider and a finger loop (target_part == "zip_pull").
  * "tab_grip"   — a rounded knob whose slot grips a small flat tab or toggle for
                   an easy push/pull (target_part == "tab_grip").

Watertight strategy: each body is one solid; the capture slot is an obround
(stadium) pocket that opens to one outer face (vents → no trapped void); the
finger loop and any pin holes are through-holes open to outer faces. Fillets are
applied to clean blanks before the pocket is cut, wrapped in try/except.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as BARE globals.
  - Read params via PARAM(lambda: <name>, <default>). No globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "key_turner"))
# key_turner | zip_pull | tab_grip

grip_len = float(PARAM(lambda: grip_len, 55.0))    # overall body length (mm)
grip_w = float(PARAM(lambda: grip_w, 24.0))        # body width across the hold (mm)
thick = float(PARAM(lambda: thick, 12.0))          # body thickness (mm)
tab_w = float(PARAM(lambda: tab_w, 9.0))           # captured tab width (key bow / pull)
tab_t = float(PARAM(lambda: tab_t, 2.4))           # captured tab thickness (slot gap)
tab_depth = float(PARAM(lambda: tab_depth, 12.0))  # how far the tab inserts
pin_dia = float(PARAM(lambda: pin_dia, 3.2))       # cross-pin/split-ring hole
loop_dia = float(PARAM(lambda: loop_dia, 14.0))    # finger loop opening (zip_pull)

# ── Clamps ───────────────────────────────────────────────────────────────────
grip_len = max(25.0, min(grip_len, 100.0))
grip_w = max(14.0, min(grip_w, 45.0))
thick = max(6.0, min(thick, 22.0))
tab_w = max(3.0, min(tab_w, 30.0))
tab_t = max(0.8, min(tab_t, 6.0))
tab_depth = max(4.0, min(tab_depth, grip_len - 8.0))
pin_dia = max(1.5, min(pin_dia, 6.0))
loop_dia = max(8.0, min(loop_dia, min(grip_w - 4.0, 30.0)))


# ── Part builders ────────────────────────────────────────────────────────────
def build_key_turner():
    """A broad rounded-rectangle wing. A key's bow slides into an obround slot at
    one end (open to that end face); a cross hole takes the key's ring/pin. The
    wide body multiplies torque so a stiff lock turns with the whole hand."""
    body = (
        cq.Workplane("XY")
        .box(grip_w, grip_len, thick, centered=(True, True, False))
    )
    # Round only the vertical edges on a clean blank (before any cut). Keep the
    # radius safely under half the width so opposite fillets never meet.
    try:
        body = body.edges("|Z").fillet(min(grip_w * 0.28, grip_w / 2.0 - 1.5, 6.0))
    except Exception:
        pass

    # Capture slot for the key bow: a thin rectangular pocket bored IN from the +Y
    # end face, centred in X and through the thickness. The slot width is kept
    # below the body width so a wall always remains on both sides (never splits
    # the end into prongs); it starts outside the +Y face so it vents to outside.
    y_end = grip_len / 2.0
    slot_w = min(tab_w, grip_w - 6.0)
    slot = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, y_end + 1.0 - tab_depth / 2.0, thick / 2.0))
        .box(slot_w, tab_depth + 2.0, tab_t, centered=(True, True, True))
    )
    body = body.cut(slot)

    # Cross pin hole through the thickness to trap the key with a split ring/pin.
    pin = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, y_end - tab_depth * 0.5, -1.0))
        .circle(pin_dia / 2.0)
        .extrude(thick + 2.0)
    )
    body = body.cut(pin)
    return body


def build_zip_pull():
    """A teardrop pull: a rounded body with a finger-loop through-hole and a small
    bar-slot at the narrow end that hooks a zipper slider's pull-hole."""
    # Teardrop = big disc unioned to a small disc, overlapping (no tangent seam).
    big_r = grip_w / 2.0
    small_r = max(3.0, grip_w * 0.22)
    reach = grip_len - big_r - small_r
    body = cq.Workplane("XY").circle(big_r).extrude(thick)
    tip = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, reach, 0))
        .circle(small_r)
        .extrude(thick)
    )
    # A connecting bar so the two lobes overlap into one solid.
    bar = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, reach / 2.0, 0))
        .box(small_r * 1.6, reach + 0.2, thick, centered=(True, True, False))
    )
    body = body.union(bar).union(tip)
    try:
        body = body.edges(">Z or <Z").fillet(min(1.4, thick * 0.2))
    except Exception:
        pass

    # Finger loop: a through-hole in the big lobe.
    loop = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -big_r * 0.15, -1.0))
        .circle(loop_dia / 2.0)
        .extrude(thick + 2.0)
    )
    body = body.cut(loop)

    # Zipper-hook slot: a small obround through-slot across the tip lobe so the
    # zip slider's pull-hole threads onto it (open through the thickness → vented).
    hook = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, reach + small_r * 0.1, -1.0))
        .slot2D(max(tab_w, tab_t + 0.01), tab_t, angle=90)
        .extrude(thick + 2.0)
    )
    body = body.cut(hook)
    return body


def build_tab_grip():
    """A rounded knob column whose slot grips a small flat tab or cord toggle so
    it can be pushed/pulled with a light pinch. The slot opens to the bottom face
    (vented); a cross pin locks the tab in.

    The knob is a single loft from a flat base circle up through a barrel to a
    smaller — but non-zero — flat top disc (loft-to-flat idiom, never a singular
    point), so it is one watertight solid with flat caps top and bottom."""
    r = grip_w / 2.0
    # Radius profile: base r → slight barrel bulge → smaller flat top. All radii
    # are strictly positive, so the loft has no singular apex.
    profile = [
        (0.00, r * 0.94),
        (0.20, r * 1.00),
        (0.55, r * 0.92),
        (0.82, r * 0.72),
        (1.00, r * 0.50),
    ]
    wp = cq.Workplane("XY")
    prev_z = 0.0
    for idx, (t, rr) in enumerate(profile):
        z = t * grip_len
        wp = wp.workplane(offset=(z - prev_z)) if idx > 0 else wp
        wp = wp.circle(rr)
        prev_z = z
    body = wp.loft(combine=True)

    # Capture slot bored up +Z from below z=0 into the lower column (vents to the
    # bottom face → no trapped void). Kept narrow enough to leave side walls.
    slot_depth = min(tab_depth, grip_len * 0.55)
    slot = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -0.5))
        .box(min(tab_w, grip_w - 5.0), tab_t, slot_depth + 0.5,
             centered=(True, True, False))
    )
    body = body.cut(slot)

    # Cross pin through the lower column (Y direction) to trap the tab. Spans the
    # full width so it opens to both curved faces → vented through-hole.
    pin = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, min(tab_depth * 0.5, slot_depth - 1.0), 0))
        .circle(pin_dia / 2.0)
        .extrude(grip_w + 4.0, both=True)
    )
    body = body.cut(pin)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "zip_pull":
    result = build_zip_pull()
elif target_part == "tab_grip":
    result = build_tab_grip()
else:  # "key_turner"
    result = build_key_turner()
