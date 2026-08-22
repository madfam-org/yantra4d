"""Garter Clip — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The two-part suspender grip on every garter belt, sock suspender and shirt stay: a nub
plate carrying a mushroom-headed button, and a loop plate with a keyhole slot. You drape
the stocking welt over the nub, drop the loop plate's wide eye over the head, then slide
it so the narrow throat of the keyhole traps the nub — the fabric is pinched between the
two plates and cannot slip. This is the rigid hard good the Fashion Cabinet `garter-clip`
notion places and bridges to here for its geometry.

Modes (dispatched via `target_part`):
  * "set"  — nub plate and loop plate laid out side by side on one plate.
  * "nub"  — the plate with the button post, mushroom head, and its webbing slot.
  * "loop" — the keyhole loop plate that traps the nub.

Geometry: both plates are rounded slabs. The keyhole is ONE cut built from two overlapping
prisms (a circle and a slot) so no sliver survives between them, overshooting both faces.
The button head is a lofted frustum plus a flat cap — never a sphere cap, whose pole
singularity reads non-watertight. Rim breaks happen on clean blanks before any hole is cut.
The webbing slot on the nub plate is the flange edge the garter strap threads over.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `strap_w`).
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
strap_w    = float(PARAM(lambda: strap_w,    12.0))  # garter strap / elastic width (mm)
strap_t    = float(PARAM(lambda: strap_t,    1.4))   # strap thickness (mm)
plate_t    = float(PARAM(lambda: plate_t,    2.4))   # plate thickness (mm)
nub_d      = float(PARAM(lambda: nub_d,      5.0))   # button post diameter (mm)
head_over  = float(PARAM(lambda: head_over,  2.2))   # head overhang past the post (mm)
grip_clear = float(PARAM(lambda: grip_clear, 0.35))  # keyhole running clearance (mm)

target_part = str(PARAM(lambda: target_part, "set"))  # set|nub|loop

# ── Safe clamps ──────────────────────────────────────────────────────────────
strap_w    = max(6.0, min(strap_w, 30.0))
strap_t    = max(0.6, min(strap_t, 4.0))
plate_t    = max(1.5, min(plate_t, 5.0))
nub_d      = max(3.0, min(nub_d, 12.0))
head_over  = max(1.0, min(head_over, 5.0))
grip_clear = max(0.15, min(grip_clear, 0.8))

# ── Derived geometry ─────────────────────────────────────────────────────────
head_d     = nub_d + 2.0 * head_over               # mushroom head diameter (mm)
# The post must stand clear of BOTH plates plus the fabric caught between them,
# otherwise the loop plate cannot seat over the head.
fabric_gap = max(0.8, strap_t * 1.2)
post_h     = plate_t + fabric_gap
head_h     = max(1.2, head_over * 0.75)
wall       = max(2.0, nub_d * 0.42)                # rail thickness around holes/slots

plate_w    = max(head_d + 2.0 * wall, strap_w + 2.0 * wall)   # plate width (Y)
slot_x     = max(strap_t * 2.0 + 1.0, 2.6)         # strap slot opening (X)
slot_y     = strap_w + 0.8                         # strap slot span (Y)
corner_r   = min(2.5, wall * 0.7)

# Nub plate: the button at one end, the strap slot at the other.
nub_len    = head_d / 2.0 + wall + slot_x + 2.0 * wall + 3.0
# Loop plate keyhole: wide eye clears the head, narrow throat traps the post.
eye_d      = head_d + 2.0 * grip_clear
throat_w   = nub_d + grip_clear
travel     = eye_d / 2.0 + throat_w * 0.6 + 2.0    # slide distance eye -> throat
loop_len   = eye_d / 2.0 + travel + throat_w / 2.0 + wall + 3.0


def _rounded_plate(length, width, thick, rad):
    """Rounded-rectangle plate, X = length, Y = width, resting on Z = 0."""
    r = max(0.3, min(rad, min(length, width) / 2.0 - 0.3))
    body = (
        cq.Workplane("XY")
        .rect(length, width)
        .extrude(thick)
        .edges("|Z")
        .fillet(r)
    )
    # Break the rim on the CLEAN blank, before any hole is cut.
    try:
        body = body.edges("#Z").chamfer(min(0.5, thick * 0.18, rad * 0.3))
    except Exception:
        pass
    return body


def build_nub():
    """Plate + button post + lofted mushroom head + strap slot."""
    body = _rounded_plate(nub_len, plate_w, plate_t, corner_r).translate(
        (nub_len / 2.0 - head_d / 2.0 - wall, 0.0, 0.0))

    # Post: overlaps into the plate by 1 mm so the union is solid, not tangent.
    post = (
        cq.Workplane("XY")
        .circle(nub_d / 2.0)
        .extrude(post_h + 1.0)
        .translate((0.0, 0.0, plate_t - 1.0))
    )
    # Head: a frustum flaring out, then a flat cap. No sphere anywhere.
    head = (
        cq.Workplane("XY")
        .workplane(offset=plate_t + post_h - 0.3)
        .circle(nub_d / 2.0)
        .workplane(offset=head_h)
        .circle(head_d / 2.0)
        .loft(ruled=True)
    )
    cap = (
        cq.Workplane("XY")
        .circle(head_d / 2.0)
        .extrude(max(0.8, head_h * 0.5))
        .translate((0.0, 0.0, plate_t + post_h + head_h - 0.3))
    )
    body = body.union(post).union(head).union(cap)

    # Strap slot: the flange edge the garter elastic threads over. Cut clean through.
    slot_cx = nub_len - head_d / 2.0 - wall - wall - slot_x / 2.0
    slot = (
        cq.Workplane("XY")
        .box(slot_x, slot_y, plate_t + 8.0)
        .translate((slot_cx, 0.0, plate_t / 2.0))
    )
    return body.cut(slot)


def build_loop():
    """Plate with a keyhole: a wide eye that clears the head, a throat that traps it."""
    body = _rounded_plate(loop_len, plate_w, plate_t, corner_r).translate(
        (loop_len / 2.0 - eye_d / 2.0 - wall, 0.0, 0.0))

    # Keyhole as ONE cutter: eye circle + throat slot, deliberately OVERLAPPING so
    # no sliver of material survives at their junction.
    eye = (
        cq.Workplane("XY")
        .circle(eye_d / 2.0)
        .extrude(plate_t + 8.0)
        .translate((0.0, 0.0, -4.0))
    )
    throat = (
        cq.Workplane("XY")
        .box(travel + eye_d / 2.0, throat_w, plate_t + 8.0)
        .translate(((travel + eye_d / 2.0) / 2.0 - 0.5, 0.0, plate_t / 2.0))
    )
    # Round the throat's blind end so the trapped post seats on an arc, not a corner.
    throat_end = (
        cq.Workplane("XY")
        .circle(throat_w / 2.0)
        .extrude(plate_t + 8.0)
        .translate((travel, 0.0, -4.0))
    )
    keyhole = eye.union(throat).union(throat_end)
    body = body.cut(keyhole)

    # Thumb ridge at the far end: a flat-topped lofted rib to push the slide home.
    ridge_cx = loop_len - eye_d / 2.0 - wall - 2.0
    ridge = (
        cq.Workplane("XY")
        .workplane(offset=plate_t - 0.3)
        .rect(2.4, plate_w - 2.0 * corner_r)
        .workplane(offset=max(0.7, plate_t * 0.35))
        .rect(1.2, plate_w - 2.0 * corner_r)
        .loft(ruled=True)
        .translate((ridge_cx, 0.0, 0.0))
    )
    return body.union(ridge)


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "nub":
    result = build_nub()
elif target_part == "loop":
    result = build_loop()
else:
    gap = max(4.0, plate_w * 0.22)
    nub = build_nub().translate((0.0, plate_w / 2.0 + gap / 2.0, 0.0))
    loop = build_loop().translate((0.0, -(plate_w / 2.0 + gap / 2.0), 0.0))
    result = cq.Workplane("XY").add(nub).add(loop)
