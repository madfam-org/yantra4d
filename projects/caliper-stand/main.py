"""
Caliper Base Stand — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A bench stand that holds a caliper for repeated gauging: drop the caliper beam
into a cradle for hands-free reading, pinch it in a beam clamp to lock it against
a reference, or stand it beam-up on a depth base to use the caliper as a poor-
man's height gauge. Sized to a standard 150 mm digital caliper beam.

Real dimensions (150 mm digital caliper, DIN 862 class):
  - beam cross-section ≈ 16 mm wide × 11 mm thick (a common 150 mm caliper is
    ~237 × 76 × 11 mm overall; the beam is the ~11 mm-thick spine)
  - the pocket is cut at beam nominal + a per-side clearance so the beam drops in
  - the beam clamp closes a saw slit onto the beam to lock the reading.

Watertight strategy:
  Every part is a filleted base blank with a rectangular POCKET cut from the top
  (blind pocket open to the top face → vents to outside, never a trapped void).
  The beam clamp adds a through saw SLIT to the pocket and a through cross SCREW.
  The depth base cuts a vertical beam SLOT clean through. Mount holes are through-
  holes vented to a face. Fillets on clean blanks BEFORE cuts, in try/except.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected; params arrive as BARE globals.
  - Read every param via PARAM(lambda: <name>, <default>).
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters (standard 150 mm caliper beam) ────────────────────────────────
target_part = str(PARAM(lambda: target_part, "jaw_cradle"))
# "jaw_cradle" | "beam_clamp" | "depth_base"

beam_w = float(PARAM(lambda: beam_w, 16.0))           # caliper beam width, mm
beam_t = float(PARAM(lambda: beam_t, 11.0))           # caliper beam thickness, mm
fit_clear = float(PARAM(lambda: fit_clear, 0.4))      # per-side pocket clearance
base_len = float(PARAM(lambda: base_len, 70.0))       # stand length along beam, mm
base_thick = float(PARAM(lambda: base_thick, 12.0))   # base plate thickness, mm
wall = float(PARAM(lambda: wall, 6.0))                # pocket wall thickness
clamp_screw_d = float(PARAM(lambda: clamp_screw_d, 4.3))  # clamp/mount screw (M4)

# Clamp to sane ranges so extreme UI values never crash the kernel.
beam_w = max(10.0, min(beam_w, 28.0))
beam_t = max(6.0, min(beam_t, 18.0))
fit_clear = max(0.1, min(fit_clear, 1.0))
base_len = max(40.0, min(base_len, 140.0))
base_thick = max(8.0, min(base_thick, 30.0))
wall = max(4.0, min(wall, 14.0))
clamp_screw_d = max(2.5, min(clamp_screw_d, 8.0))

_pw = beam_w + 2.0 * fit_clear        # pocket width
_pt = beam_t + 2.0 * fit_clear        # pocket depth (into the beam thickness)


# ── Base blank ───────────────────────────────────────────────────────────────
def _base_blank(width, length, height, fillet_r=None):
    """A clean filleted base block, base at z=0. Fillet the vertical edges of the
    CLEAN blank before any pocket/slot cuts (fillet-on-feature crashes clean())."""
    blank = (
        cq.Workplane("XY")
        .box(width, length, height, centered=(True, True, False))
    )
    r = fillet_r if fillet_r is not None else min(4.0, wall * 0.5)
    try:
        blank = blank.edges("|Z").fillet(r)
    except Exception:
        pass
    return blank


def _corner_mounts(body, width, length, height):
    """Through mount holes near the four corners, vented top↔bottom."""
    ox = width / 2.0 - wall * 0.75
    oy = length / 2.0 - wall * 0.75
    if ox <= clamp_screw_d or oy <= clamp_screw_d:
        return body
    for sx in (-1, 1):
        for sy in (-1, 1):
            hole = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(sx * ox, sy * oy, -0.5))
                .circle(max(0.6, clamp_screw_d / 2.0 + 0.4))
                .extrude(height + 1.0)
            )
            body = body.cut(hole)
    return body


# ── Part builders ────────────────────────────────────────────────────────────
def build_jaw_cradle():
    """A hands-free cradle: a base block with a beam-shaped pocket cut in the top,
    running the length of the stand, so the caliper beam drops in and rests
    upright for reading. Open at both ends and the top → fully vented."""
    body_w = _pw + 2.0 * wall
    body_h = base_thick + _pt
    body = _base_blank(body_w, base_len, body_h)

    # Beam pocket cut from the top, through both Y ends (open channel) — the
    # caliper beam sits in it. Depth = _pt, sunk from the top face down.
    pocket = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, body_h - _pt))
        .box(_pw, base_len + 2.0, _pt + 0.5, centered=(True, True, False))
    )
    body = body.cut(pocket)
    body = _corner_mounts(body, body_w, base_len, body_h)
    return body


def build_beam_clamp():
    """A locking cradle: like the cradle but with a saw slit down one wall and a
    cross clamp screw, so tightening pinches the beam and locks the caliper
    against a reference for repeated comparison gauging."""
    body_w = _pw + 2.0 * wall
    body_h = base_thick + _pt
    body = _base_blank(body_w, base_len, body_h)

    pocket = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, body_h - _pt))
        .box(_pw, base_len + 2.0, _pt + 0.5, centered=(True, True, False))
    )
    body = body.cut(pocket)

    # Saw slit from the +X outer face inward to just past the pocket wall, full
    # length and full height of the pocket zone, so the outer wall can flex.
    slit_x = body_w / 2.0 - wall * 0.5
    slit = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(slit_x, 0, body_h - _pt * 0.9))
        .box(1.6, base_len + 2.0, _pt * 0.95, centered=(True, True, False))
    )
    body = body.cut(slit)

    # Cross clamp screw across X through the flexing wall, at pocket mid-height.
    scr_z = body_h - _pt * 0.5
    screw = (
        cq.Workplane("YZ")
        .transformed(offset=cq.Vector(0, scr_z, 0))
        .circle(max(0.6, clamp_screw_d / 2.0))
        .extrude(body_w / 2.0 + 1.0, both=True)
    )
    body = body.cut(screw)
    body = _corner_mounts(body, body_w, base_len, body_h)
    return body


def build_depth_base():
    """A height-gauge base: a wide flat reference plate with a VERTICAL beam slot
    at the centre, so the caliper stands beam-up (jaws down) and the flat base
    face is the reference datum. The slot is cut clean through the plate; a cross
    pinch screw locks the beam upright."""
    plate_w = _pw + 2.0 * wall + base_len * 0.3   # wide, stable reference foot
    plate_d = beam_w + 2.0 * wall + 20.0
    plate_h = base_thick + 6.0

    body = _base_blank(plate_w, plate_d, plate_h, fillet_r=min(6.0, plate_w * 0.1))

    # Vertical beam slot through the plate (beam stands up in it). The slot cross-
    # section is the beam cross-section grown by clearance; cut top↔bottom.
    slot = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -0.5))
        .box(_pw, _pt, plate_h + 1.0, centered=(True, True, False))
    )
    body = body.cut(slot)

    # Cross pinch screw across X through the slot at mid-height, to lock the beam.
    scr_z = plate_h * 0.55
    screw = (
        cq.Workplane("YZ")
        .transformed(offset=cq.Vector(0, scr_z, 0))
        .circle(max(0.6, clamp_screw_d / 2.0))
        .extrude(plate_w / 2.0 + 1.0, both=True)
    )
    body = body.cut(screw)
    body = _corner_mounts(body, plate_w, plate_d, plate_h)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "beam_clamp":
    result = build_beam_clamp()
elif target_part == "depth_base":
    result = build_depth_base()
else:
    result = build_jaw_cradle()
