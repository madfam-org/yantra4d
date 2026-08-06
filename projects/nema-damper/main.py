"""
NEMA Damper Mount — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A vibration-damping mount for NEMA 17 / 23 stepper motors: the motor bolts to the
plate through rubber grommets so motor noise and resonance are isolated from the
frame. Mount flat with a grommet plate, sandwich a damper spacer between motor and
frame, or stand the motor off an isolating L-bracket. Grows the `nema-stepper`
family.

NEMA stepper geometry (nominal, dimensionally real):
  - NEMA 17: body 42.3 mm sq, bolt square 31.0 mm, M3 (3.4 mm clr), pilot 22 mm
  - NEMA 23: body 57.0 mm sq, bolt square 47.14 mm, M4/M5 (5.2 mm clr), pilot 38.5 mm
  Bolt holes at the corners of the bolt square; a central pilot bore clears the
  motor's raised register boss and shaft.

Watertight strategy:
  Plates and brackets are filleted rounded slabs (fillet the clean blank BEFORE
  cutting features). Bolt holes are through-holes; grommet pockets are open
  counterbores on a face; the pilot bore is a single through-bore — all vent to
  outside, no trapped voids. The L-bracket leg + base + gusset are UNIONED with
  overlap (never tangent), with a central pillar co-located on the plate plane so
  thin raked plates bond. Wrapped in try/except.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `target_part`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals().
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


# ── NEMA motor table (case-normalised lookup) ────────────────────────────────
# body: motor body square (mm); bolt: bolt-square spacing (mm); bolt_d: mounting
# bolt clearance dia; pilot: central pilot-bore dia (clears the register boss).
NEMA_TABLE = {
    "NEMA17": {"body": 42.3, "bolt": 31.0, "bolt_d": 3.4, "pilot": 22.0},
    "NEMA23": {"body": 57.0, "bolt": 47.14, "bolt_d": 5.2, "pilot": 38.5},
}


def nema_spec(key):
    k = str(key).strip().upper().replace(" ", "").replace("-", "")
    return NEMA_TABLE.get(k, NEMA_TABLE["NEMA17"])


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "grommet_plate"))
# "grommet_plate" | "sandwich_spacer" | "bracket_isolator"

nema = str(PARAM(lambda: nema, "NEMA17"))           # NEMA17 | NEMA23
plate_t = float(PARAM(lambda: plate_t, 6.0))        # mount plate thickness
grommet_d = float(PARAM(lambda: grommet_d, 10.0))   # rubber grommet outer dia
grommet_depth = float(PARAM(lambda: grommet_depth, 3.0))  # grommet pocket depth
margin = float(PARAM(lambda: margin, 7.0))          # material around the bolt square
leg_h = float(PARAM(lambda: leg_h, 45.0))           # L-bracket leg height
frame_bolt_d = float(PARAM(lambda: frame_bolt_d, 4.5))  # frame mounting bolt clr

spec = nema_spec(nema)
body = spec["body"]
bolt_sq = spec["bolt"]
bolt_d = spec["bolt_d"]
pilot_d = spec["pilot"]

# Clamp to sane ranges so extreme UI values never crash the kernel.
plate_t = max(4.0, min(plate_t, 16.0))
grommet_d = max(bolt_d + 3.0, min(grommet_d, 18.0))
grommet_depth = max(1.5, min(grommet_depth, plate_t - 2.0))
margin = max(4.0, min(margin, 20.0))
leg_h = max(25.0, min(leg_h, 120.0))
frame_bolt_d = max(3.0, min(frame_bolt_d, 8.0))

plate_sz = bolt_sq + 2.0 * margin


# ── Helpers ──────────────────────────────────────────────────────────────────
def _bolt_pts():
    """The 4 corners of the NEMA bolt square, centred on origin."""
    h = bolt_sq / 2.0
    return [(-h, -h), (h, -h), (h, h), (-h, h)]


def _rounded_slab(sx, sy, thick, rad):
    """A slab centred on XY, base at z=0, filleted vertical edges. Fillet the
    clean blank BEFORE any feature cut."""
    blank = cq.Workplane("XY").box(sx, sy, thick, centered=(True, True, False))
    try:
        blank = blank.edges("|Z").fillet(min(rad, min(sx, sy) / 2.0 - 1.0))
    except Exception:
        pass
    return blank


def _drill_motor_face(bd, thick, from_top=True, pilot=True, grommet=True):
    """Return a cutter Workplane function is overkill; instead apply cuts to a
    body. This helper cuts the NEMA pattern into `bd` (a body) of thickness
    `thick`: 4 bolt through-holes, optional grommet counterbores, pilot bore."""
    face = ">Z" if from_top else "<Z"
    pts = _bolt_pts()
    # Bolt through-holes.
    bd = (
        bd.faces(face).workplane(centerOption="ProjectedOrigin")
        .pushPoints(pts)
        .hole(bolt_d)
    )
    # Grommet counterbores (open pockets on the face → vent).
    if grommet and grommet_d > bolt_d and grommet_depth > 0:
        bd = (
            bd.faces(face).workplane(centerOption="ProjectedOrigin")
            .pushPoints(pts)
            .cboreHole(bolt_d, grommet_d, grommet_depth)
        )
    # Central pilot bore (single through-bore → vents both faces).
    if pilot:
        bd = (
            bd.faces(face).workplane(centerOption="ProjectedOrigin")
            .circle(pilot_d / 2.0)
            .cutThruAll()
        )
    return bd


# ── Part builders ────────────────────────────────────────────────────────────
def build_grommet_plate():
    """A flat NEMA mount plate where each bolt passes through a rubber-grommet
    counterbore so the motor is vibration-isolated from the plate. Pilot bore
    clears the boss. Everything vents to outside."""
    bd = _rounded_slab(plate_sz, plate_sz, plate_t, margin * 0.6)
    bd = _drill_motor_face(bd, plate_t, from_top=True, pilot=True, grommet=True)
    return bd


def build_sandwich_spacer():
    """A damper SPACER that sits between the motor face and the frame: a plate
    with the NEMA square drilled through and grommet pockets on BOTH faces, so a
    grommet on each side sandwiches the vibration. A large central relief clears
    the boss and shaft coupling."""
    bd = _rounded_slab(plate_sz, plate_sz, plate_t, margin * 0.6)

    # Bolt through-holes.
    pts = _bolt_pts()
    bd = (
        bd.faces(">Z").workplane(centerOption="ProjectedOrigin")
        .pushPoints(pts).hole(bolt_d)
    )
    # Grommet pockets on the TOP face.
    bd = (
        bd.faces(">Z").workplane(centerOption="ProjectedOrigin")
        .pushPoints(pts).cboreHole(bolt_d, grommet_d, grommet_depth)
    )
    # Grommet pockets on the BOTTOM face (the sandwich).
    bd = (
        bd.faces("<Z").workplane(centerOption="ProjectedOrigin")
        .pushPoints(pts).cboreHole(bolt_d, grommet_d, grommet_depth)
    )
    # Central relief bore (bigger than the pilot to clear a coupling), vented.
    relief_d = min(pilot_d + 8.0, plate_sz - 2.0 * margin)
    bd = (
        bd.faces(">Z").workplane(centerOption="ProjectedOrigin")
        .circle(relief_d / 2.0).cutThruAll()
    )
    return bd


def build_bracket_isolator():
    """An L-bracket that stands the motor off a frame with grommet isolation on
    the vertical face: a vertical NEMA plate + a horizontal base with frame bolt
    slots + a gusset, all welded with overlap. A central pillar co-located on the
    base plane ties the raked leg to the base (thin plates bond)."""
    base_t = plate_t
    base_len = plate_sz
    base_depth = plate_sz * 0.7

    # Horizontal base (z in [0, base_t]).
    base = _rounded_slab(base_len, base_depth, base_t, margin * 0.5)

    # Vertical motor plate rising in +Z at the back (-Y) edge, overlapping DOWN
    # into the base so the weld is solid.
    ov = max(2.0, base_t)
    leg = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -base_depth / 2.0 + plate_t / 2.0,
                                      base_t - ov))
        .box(plate_sz, plate_t, leg_h + ov, centered=(True, True, False))
    )
    try:
        leg = leg.edges("|Y").fillet(min(margin * 0.4, plate_t * 0.4))
    except Exception:
        pass
    body_ = base.union(leg)

    # Gusset triangle each side tying the leg to the base (solid overlap).
    for sx in (-1, 1):
        gx = sx * (plate_sz / 2.0 - plate_t)
        gusset = (
            cq.Workplane("YZ")
            .transformed(offset=cq.Vector(0, 0, gx))
            .polyline([
                (-base_depth / 2.0 + plate_t, base_t),
                (-base_depth / 2.0 + plate_t + base_depth * 0.5, base_t),
                (-base_depth / 2.0 + plate_t, base_t + leg_h * 0.5),
            ]).close()
            .extrude(plate_t)
        )
        body_ = body_.union(gusset)

    # NEMA bolt pattern + grommets + pilot on the VERTICAL leg. The leg spans
    # y in [y_out, y_out + plate_t]; the motor mounts on the OUTER (-Y) face at
    # y_out. Drill along +Y as Y-axis cylinders (makeCylinder avoids workplane-
    # rotation sign confusion) so the pattern actually lands on the leg.
    y_out = -base_depth / 2.0
    z_centre = base_t + leg_h / 2.0
    hs = bolt_sq / 2.0
    pts = [(-hs, z_centre - hs), (hs, z_centre - hs),
           (hs, z_centre + hs), (-hs, z_centre + hs)]

    def _y_cyl(radius, x, z, y_start, length):
        """A cylinder whose axis runs +Y, from (x, y_start, z)."""
        return cq.Solid.makeCylinder(
            radius, length, cq.Vector(x, y_start, z), cq.Vector(0, 1, 0))

    # Bolt through-holes (full leg depth + slack, vent both leg faces).
    for (x, z) in pts:
        body_ = body_.cut(_y_cyl(bolt_d / 2.0, x, z, y_out - 1.0, plate_t + 2.0))
    # Pilot bore through the leg.
    body_ = body_.cut(_y_cyl(pilot_d / 2.0, 0.0, z_centre, y_out - 1.0, plate_t + 2.0))
    # Grommet counterbores sunk into the OUTER (-Y) face (open pocket → vents).
    for (x, z) in pts:
        body_ = body_.cut(
            _y_cyl(grommet_d / 2.0, x, z, y_out - 0.01, grommet_depth + 0.01))

    # Frame mounting slots through the base (vent through base thickness).
    for sx in (-1, 1):
        slot = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(sx * plate_sz * 0.28,
                                          base_depth * 0.22, -1.0))
            .slot2D(min(base_depth * 0.4, 18.0), frame_bolt_d, angle=90)
            .extrude(base_t + 2.0)
        )
        body_ = body_.cut(slot)
    return body_


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "sandwich_spacer":
    result = build_sandwich_spacer()
elif target_part == "bracket_isolator":
    result = build_bracket_isolator()
else:
    result = build_grommet_plate()
