"""
GoPro-Style Mount Fingers — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The de-facto action-cam mounting standard: interlocking "finger" clevis joints
joined by a thumbscrew through the knuckle. A 2-prong (female) and 3-prong (male)
interleave on a shared finger pitch, then a bolt through the aligned 5 mm holes
pivots and clamps them. This cartridge builds both prongs, a flat mounting base
plate, and the ubiquitous 1/4-20 tripod adapter.

Real GoPro finger spec modelled here:
  - finger thickness      ≈ 3.0 mm
  - gap between fingers    ≈ 3.2 mm  (a mating 3.0 mm finger nests with 0.1 mm/side)
  - knuckle diameter       ≈ 15 mm   (radius ≈ 7.5 mm), rounded top
  - axle bolt through-hole = 5.0 mm  (common M5 thumbscrew)
  - pitch = thickness + gap ≈ 6.2 mm so 2-prong and 3-prong interleave.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `finger_thick`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
  - Assign the final solid to a top-level name `result`.
"""



import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default.
    `except Exception` catches the NameError raised for an unbound param name
    (the sandbox does not expose globals()/NameError directly)."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters (GoPro finger standard) ───────────────────────────────────────
finger_thick = float(PARAM(lambda: finger_thick, 3.0))   # single finger thickness (X)
finger_gap   = float(PARAM(lambda: finger_gap,   3.2))   # gap between fingers (mating clearance)
knuckle_d    = float(PARAM(lambda: knuckle_d,   15.0))   # rounded knuckle diameter
bolt_hole_d  = float(PARAM(lambda: bolt_hole_d,  5.0))   # axle / thumbscrew through-hole (M5)
reach        = float(PARAM(lambda: reach,       18.0))   # knuckle-centre height above base top
base_thick   = float(PARAM(lambda: base_thick,   4.0))   # base slab thickness (Z)
base_len     = float(PARAM(lambda: base_len,    30.0))   # base length along Y (reach direction)
base_margin  = float(PARAM(lambda: base_margin,  4.0))   # base overhang beyond the finger span (X & +Y)

# base_plate extras
plate_len    = float(PARAM(lambda: plate_len,   40.0))   # flat mounting-plate length (Y)
plate_width  = float(PARAM(lambda: plate_width, 40.0))   # flat mounting-plate width (X)
screw_holes  = bool( PARAM(lambda: screw_holes, True))   # add corner screw holes to base_plate
screw_hole_d = float(PARAM(lambda: screw_hole_d, 4.2))   # M4 clearance for the plate screw holes

# quarter20 adapter
adapter_prongs = str(PARAM(lambda: adapter_prongs, "triple"))  # "dual" | "triple" on the adapter
quarter20_d    = float(PARAM(lambda: quarter20_d, 5.5))        # 1/4-20 tapping/clearance socket (cosmetic)
quarter20_depth = float(PARAM(lambda: quarter20_depth, 8.0))   # socket depth from underside

target_part  = str(PARAM(lambda: target_part, "dual"))
# "dual" | "triple" | "base_plate" | "quarter20_adapter"


# ── Derived / clamped geometry ───────────────────────────────────────────────
knuckle_r = max(1.0, knuckle_d / 2.0)
# The bolt hole cannot approach the knuckle rim — keep at least 1.2 mm of wall.
bolt_r = min(max(0.5, bolt_hole_d / 2.0), knuckle_r - 1.2)
# Finger pitch: one thickness + one gap. A mating finger (thickness) drops into
# the gap of the opposite prong, so interleave is valid whenever gap >= thickness.
pitch = finger_thick + finger_gap
# Shaft width (Y) below the knuckle — a touch under the knuckle so the round reads.
shaft_w = knuckle_d * 0.92


# ── Core finger primitive ────────────────────────────────────────────────────
def _finger(x_center):
    """One GoPro finger standing in +Z, pivot (knuckle) axis along X.

    Geometry is built centred on the pivot axis at Z = 0 then lifted so the
    knuckle centre sits at Z = reach above the base top. A rectangular shaft
    joins the rounded knuckle down to the base; the axle hole runs along X.
    """
    # Knuckle: cylinder whose axis is X, centred on the pivot.
    knuckle = (
        cq.Workplane("YZ")
        .circle(knuckle_r)
        .extrude(finger_thick / 2.0, both=True)
    )
    # Shaft: from the pivot down past the base top (extra so it fuses into base).
    shaft_h = reach + base_thick  # reaches from pivot down to below the base top
    shaft = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -shaft_h / 2.0))
        .box(finger_thick, shaft_w, shaft_h, centered=(True, True, True))
    )
    finger = knuckle.union(shaft)

    # Axle through-hole along X.
    hole = (
        cq.Workplane("YZ")
        .circle(bolt_r)
        .extrude(finger_thick, both=True)
    )
    finger = finger.cut(hole)

    # Lift so the pivot sits at Z = reach, then shift to its X slot.
    finger = finger.translate((x_center, 0, reach))
    return finger


def _finger_bank(n_slots, filled):
    """Union a set of fingers on the shared pitch grid.

    `n_slots` slots are laid out symmetric about X = 0; `filled` is the list of
    slot indices that carry a finger (0-based, left→right)."""
    span = (n_slots - 1) * pitch
    x0 = -span / 2.0
    bank = None
    for i in filled:
        f = _finger(x0 + i * pitch)
        bank = f if bank is None else bank.union(f)
    return bank


def _finger_x_extent(n_slots):
    """Half-extent in X of the outermost fingers (for sizing bases)."""
    span = (n_slots - 1) * pitch
    return span / 2.0 + finger_thick / 2.0


# ── Bases ────────────────────────────────────────────────────────────────────
def _mount_base(x_half):
    """A slab under the fingers. Sits with its top at Z = 0 (fingers grow from it),
    spanning the finger X extent (+margin) and `base_len` in Y (+margin toward +Y
    so the mount has meat behind the pivot)."""
    bx = 2.0 * (x_half + base_margin)
    by = base_len
    # Centre the slab so the pivot (Y = 0) sits near its +Y edge region.
    base = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -by / 2.0 + base_margin, -base_thick / 2.0))
        .box(bx, by, base_thick, centered=(True, True, True))
    )
    try:
        base = base.edges("|Z").fillet(min(2.5, base_margin - 0.5))
    except Exception:
        pass
    return base


def build_prongs(kind):
    """kind = 'dual' (2 fingers, outer slots of a 3-slot grid) or
    'triple' (3 fingers filling a 3-slot grid). Both share the pitch grid so a
    dual and a triple interleave: the triple's centre finger drops into the
    dual's gap; the triple's outer fingers sit outside the dual's pair."""
    n_slots = 3
    if kind == "dual":
        filled = [0, 2]
    else:
        filled = [0, 1, 2]
    bank = _finger_bank(n_slots, filled)
    base = _mount_base(_finger_x_extent(n_slots))
    solid = base.union(bank)
    return solid


def build_base_plate():
    """Fingers on a flat rectangular plate with optional corner screw holes —
    for adhesive or screw mounting to a surface. Uses the 3-prong (male) bank,
    the more common adhesive-mount configuration."""
    n_slots = 3
    bank = _finger_bank(n_slots, [0, 1, 2])

    # Flat plate, top at Z = 0.
    plate = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -base_thick / 2.0))
        .box(plate_width, plate_len, base_thick, centered=(True, True, True))
    )
    try:
        plate = plate.edges("|Z").fillet(min(3.0, plate_width / 2.0 - 0.5, plate_len / 2.0 - 0.5))
    except Exception:
        pass

    if screw_holes:
        hr = max(0.5, screw_hole_d / 2.0)
        inset = max(hr + 2.0, 5.0)
        hx = plate_width / 2.0 - inset
        hy = plate_len / 2.0 - inset
        for sx in (-hx, hx):
            for sy in (-hy, hy):
                hole = (
                    cq.Workplane("XY")
                    .transformed(offset=cq.Vector(sx, sy, -base_thick / 2.0))
                    .circle(hr)
                    .extrude(base_thick * 2.0, both=True)
                )
                plate = plate.cut(hole)

    return plate.union(bank)


def build_quarter20_adapter():
    """GoPro prongs on top of a puck that carries a 1/4-20 socket underneath —
    the ubiquitous camera↔tripod adapter. The 1/4-20 hole is modelled as a plain
    cylindrical socket (cosmetic nominal envelope, no slow swept helix)."""
    n_slots = 3
    filled = [0, 2] if adapter_prongs == "dual" else [0, 1, 2]
    bank = _finger_bank(n_slots, filled)

    # Puck sized to cover the finger span; a bit deeper so the 1/4-20 socket fits.
    x_half = _finger_x_extent(n_slots)
    puck_x = 2.0 * (x_half + base_margin)
    puck_y = max(base_len, quarter20_d + 2.0 * base_margin + 6.0)
    puck_h = max(base_thick, quarter20_depth + 3.0)

    puck = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -puck_y / 2.0 + base_margin, -puck_h / 2.0))
        .box(puck_x, puck_y, puck_h, centered=(True, True, True))
    )
    try:
        puck = puck.edges("|Z").fillet(min(3.0, base_margin - 0.5))
    except Exception:
        pass

    # 1/4-20 socket bored up from the underside, centred under the pivot (Y = 0).
    q_r = max(0.5, quarter20_d / 2.0)
    q_depth = min(quarter20_depth, puck_h - 1.5)
    socket = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -puck_h + q_depth / 2.0))
        .circle(q_r)
        .extrude(q_depth / 2.0, both=True)
    )
    puck = puck.cut(socket)

    return puck.union(bank)


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "triple":
    result = build_prongs("triple")
elif target_part == "base_plate":
    result = build_base_plate()
elif target_part == "quarter20_adapter":
    result = build_quarter20_adapter()
else:  # "dual"
    result = build_prongs("dual")
