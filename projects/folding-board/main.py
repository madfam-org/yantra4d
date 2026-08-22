"""Folding Board — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The garment folding board: a centre panel with a hinged wing on each side, so a shirt laid
face-down is folded to an identical rectangle every time. Retail folding boards come in one
size, which is why a folded child's tee and a folded XXL sweatshirt never stack; this one is
generated from the target folded width and height.

The hinge is a real pin knuckle, not a living hinge: each panel carries interleaved knuckles
and a printed pin passes through them. Three parts, printed flat, assembled in a minute.

Modes (dispatched via `target_part`):
  * "center_panel" — the fixed middle panel with its two knuckle rows.
  * "side_panel"   — one wing (print two, mirrored by flipping on the bed).
  * "pin"          — one hinge pin (print two, or four with a spare).
  * "set"          — all three laid out on one plate as separate bodies.

Geometry: every panel is a rounded-rect plate; knuckles are cylinders with an overlapping
root block so nothing is ever tangent; the pin bore is one cut that overshoots both ends.
No fillets after cuts, no sealed voids, no cylinder+sphere caps.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `fold_w`).
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
fold_w   = float(PARAM(lambda: fold_w,   200.0))  # finished folded width (mm)
fold_h   = float(PARAM(lambda: fold_h,   280.0))  # finished folded height (mm)
panel_t  = float(PARAM(lambda: panel_t,  4.0))    # panel thickness (mm)
pin_dia  = float(PARAM(lambda: pin_dia,  4.0))    # hinge pin diameter (mm)
knuckles = int(  PARAM(lambda: knuckles, 3))      # knuckles per hinge on the centre panel
lighten  = bool( PARAM(lambda: lighten,  True))   # cut lightening windows in the panels

target_part = str(PARAM(lambda: target_part, "set"))


# ── Safe clamps ──────────────────────────────────────────────────────────────
# A folded child's tee is about 140 x 200; a folded XXL sweatshirt about 320 x 420.
fold_w   = max(120.0, min(fold_w, 340.0))
fold_h   = max(160.0, min(fold_h, 460.0))
panel_t  = max(2.5,   min(panel_t, 8.0))
pin_dia  = max(2.5,   min(pin_dia, 8.0))
# The pin can never be fatter than the panel it lives in, or the knuckle has no wall.
pin_dia  = min(pin_dia, max(2.0, panel_t * 1.6))
knuckles = max(2,     min(knuckles, 5))

# ── Derived geometry ─────────────────────────────────────────────────────────
# The centre panel is the finished folded width; each wing folds the sleeve in, so a
# wing is a bit under half the centre width — that is what makes the fold overlap.
center_w = fold_w
wing_w   = max(40.0, center_w * 0.46)
panel_h  = fold_h
corner_r = min(12.0, min(center_w, panel_h) * 0.08)

# Knuckle geometry. The knuckle barrel is a cylinder whose axis runs along Y (the hinge
# line), rooted in a block that overlaps the panel edge by a real depth.
knuckle_r  = max(pin_dia / 2.0 + 1.2, panel_t * 0.75)
hinge_len  = panel_h * 0.72                      # the hinge line spans most of the height
seg        = hinge_len / float(knuckles * 2 - 1)  # centre and wing knuckles interleave
knuckle_gap = 0.4                                 # per-side running clearance
pin_clear   = 0.35                                # pin-to-bore diametral clearance
root_d      = knuckle_r * 1.6                     # how far the knuckle root bites into the panel


def _plate(width, height, thick, rad):
    """A rounded-rect plate lying in XY, centred at the origin, `thick` along Z."""
    r = max(0.5, min(rad, min(width, height) / 2.0 - 0.5))
    return (
        cq.Workplane("XY")
        .rect(width, height)
        .extrude(thick)
        .translate((0, 0, -thick / 2.0))
        .edges("|Z")
        .fillet(r)
    )


def _lighten(plate, width, height):
    """Cut lightening windows so a big board is not a solid slab of filament.

    Cutters overshoot BOTH faces in Z. Windows are inset far enough that the remaining
    frame is never thinner than three perimeters at any wall.
    """
    frame = max(10.0, min(width, height) * 0.10)
    win_w = width - 2.0 * frame
    win_h = (height - 3.0 * frame) / 2.0
    if win_w < 20.0 or win_h < 20.0:
        return plate
    over = panel_t + 6.0
    for sy in (-1.0, 1.0):
        cy = sy * (win_h / 2.0 + frame / 2.0)
        cut = (
            cq.Workplane("XY")
            .rect(win_w, win_h)
            .extrude(over)
            .translate((0, cy, -over / 2.0))
            .edges("|Z")
            .fillet(min(8.0, min(win_w, win_h) / 2.0 - 0.5))
        )
        plate = plate.cut(cut)
    return plate


def _knuckle_row(x_edge, parity, count):
    """Interleaved knuckle barrels along the hinge line at panel edge `x_edge`.

    `parity` 0 takes the even segments, 1 the odd ones, so a centre-panel row and a
    wing row mesh without touching. Each barrel is a cylinder along Y unioned with a
    root block that OVERLAPS the panel by `root_d` — never a tangent contact.
    """
    body = None
    y0 = -hinge_len / 2.0
    for i in range(count):
        idx = 2 * i + parity
        if idx > knuckles * 2 - 2:
            break
        yc = y0 + (idx + 0.5) * seg
        length = seg - 2.0 * knuckle_gap
        if length <= 0.8:
            continue
        barrel = (
            cq.Workplane("XZ")
            .circle(knuckle_r)
            .extrude(length)
            .translate((x_edge, yc - length / 2.0, 0))
        )
        # Root block: a slab from the barrel axis back into the panel, overlapping.
        root = (
            cq.Workplane("XY")
            .box(root_d, length, knuckle_r * 2.0)
            .translate((x_edge - root_d / 2.0 if x_edge > 0 else x_edge + root_d / 2.0,
                        yc, 0))
        )
        piece = barrel.union(root)
        body = piece if body is None else body.union(piece)
    return body


def _bore(solid, x_edge):
    """Bore the pin hole along the hinge axis, overshooting both ends of the row."""
    over = hinge_len + 40.0
    bore = (
        cq.Workplane("XZ")
        .circle((pin_dia + pin_clear) / 2.0)
        .extrude(over)
        .translate((x_edge, -over / 2.0, 0))
    )
    return solid.cut(bore)


def build_center_panel():
    """The middle panel: a plate with an interleaving knuckle row on each edge."""
    plate = _plate(center_w, panel_h, panel_t, corner_r)
    if lighten:
        plate = _lighten(plate, center_w, panel_h)
    body = plate
    for sx in (-1.0, 1.0):
        x_edge = sx * center_w / 2.0
        row = _knuckle_row(x_edge, 0, knuckles)
        if row is not None:
            body = body.union(row)
            body = _bore(body, x_edge)
    return body


def build_side_panel():
    """One wing: a plate with the complementary knuckle row on its inboard edge.

    The wing is built with its hinge on the -X edge so it drops straight onto the
    centre panel's +X hinge line; print two and flip one on the bed.
    """
    plate = _plate(wing_w, panel_h, panel_t, corner_r)
    if lighten:
        plate = _lighten(plate, wing_w, panel_h)
    x_edge = -wing_w / 2.0
    body = plate
    row = _knuckle_row(x_edge, 1, knuckles)
    if row is not None:
        body = body.union(row)
        body = _bore(body, x_edge)
    return body


def build_pin():
    """One hinge pin: a plain rod with a lead-in chamfer wedge and a small head.

    The chamfer is a lofted frustum on a CLEAN blank (never a `.chamfer()` after a
    cut), and the head is a short fatter cylinder that stops the pin walking out.
    """
    length = hinge_len + 2.0
    r = pin_dia / 2.0
    shaft = (
        cq.Workplane("XY")
        .circle(r)
        .extrude(length)
    )
    # Lead-in: a frustum tapering to a small FLAT circle at the free end.
    lead = min(pin_dia * 0.8, 3.0)
    tip = (
        cq.Workplane("XY")
        .workplane(offset=length - lead)
        .circle(r)
        .workplane(offset=lead)
        .circle(max(0.5, r * 0.55))
        .loft(ruled=True)
    )
    body = shaft.cut(
        cq.Workplane("XY")
        .circle(r + 2.0)
        .extrude(lead + 1.0)
        .translate((0, 0, length - lead))
    ).union(tip)
    # Head: a fatter stub at the entry end, overlapping the shaft.
    head_r = min(r + 1.2, knuckle_r * 0.9)
    head = (
        cq.Workplane("XY")
        .circle(head_r)
        .extrude(min(2.0, pin_dia * 0.6) + r)
        .translate((0, 0, -r))
    )
    return body.union(head)


def build_set():
    """All three parts laid out flat on one plate as genuinely separate bodies.

    They are combined as a Compound — never `.union()` of non-touching solids, which
    produces a nominally single shape with disjoint shells.
    """
    gap = max(12.0, panel_t * 4.0)
    center = build_center_panel()
    wing = build_side_panel()
    pin = build_pin().rotate((0, 0, 0), (1, 0, 0), -90)  # lay the pin flat along +Y

    x_center = 0.0
    x_wing = center_w / 2.0 + wing_w / 2.0 + gap + knuckle_r * 2.0
    x_pin = x_wing + wing_w / 2.0 + gap + knuckle_r * 2.0

    placed = [
        center.translate((x_center, 0, 0)),
        wing.translate((x_wing, 0, 0)),
        pin.translate((x_pin, -hinge_len / 2.0, 0)),
    ]
    solids = []
    for wp in placed:
        for s in wp.vals():
            solids.append(s)
    return cq.Workplane(obj=cq.Compound.makeCompound(solids))


# ── Dispatch ─────────────────────────────────────────────────────────────────
# Mode ids and part ids match the manifest exactly — the platform injects
# `target_part` once per id in the active mode's parts[] array:
#   center_panel -> parts ["center_panel"]
#   side_panel   -> parts ["side_panel"]
#   pin          -> parts ["pin"]
#   set          -> parts ["set"]   (one plate carrying all three as a Compound)
if target_part == "center_panel":
    result = build_center_panel()
elif target_part == "side_panel":
    result = build_side_panel()
elif target_part == "pin":
    result = build_pin()
else:
    result = build_set()
