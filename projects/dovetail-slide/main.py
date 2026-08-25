"""
Dovetail Optics Slide — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A 60° dovetail translation slide for optics and light tooling: a male dovetail
rail (the track), a female carriage that rides on it, and a clamping carriage
that pinches the dovetail with a gib screw to lock the position. This is the
open, printable analogue of a Thorlabs RC-series / XT-style optical dovetail —
the de-facto lab standard is a 60° prismatic dovetail so posts, carriers and
translators all interoperate on one rail.

Dovetail geometry (dimensionally real, optics-dovetail convention):
  - included dovetail flank angle    = 60°  (30° from vertical each side — the
    lab-standard optical dovetail; a gib/carriage grips the two 60° flanks)
  - rail top width (narrow face)     ≈ 20 mm nominal (RC/XT class rails run
    ~15–25 mm; parametric here)
  - the male rail is WIDER at the base than the top (undercut), so a female
    dovetail cannot lift off — it can only translate along the rail axis (Y).

Watertight strategy:
  Rail, carriage and clamp are all extruded 2D dovetail cross-sections (built
  from polyline trapezoids — never revolved grooves). The carriage's female
  channel is a through-channel open at both Y ends (vents to outside). Mounting
  bolt holes are through-holes vented to a face. The clamp's gib slit and cross
  screw are through-features. Fillets are applied to clean blanks BEFORE feature
  cuts, wrapped in try/except so an extreme parameter can never crash clean().

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params are injected as BARE names.
  - Read every param via PARAM(lambda: <name>, <default>) — globals()/eval are
    NOT in the sandbox's allowed builtins.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq
import math


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default. `except Exception`
    catches the NameError the sandbox raises for an unbound param name."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters (60° optical dovetail) ────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "rail"))
# "rail" | "carriage" | "clamp"

dovetail_w = float(PARAM(lambda: dovetail_w, 20.0))   # rail TOP (narrow) width, mm
dovetail_ang = float(PARAM(lambda: dovetail_ang, 60.0))  # included flank angle, deg
rail_h = float(PARAM(lambda: rail_h, 10.0))           # rail / dovetail height, mm
rail_len = float(PARAM(lambda: rail_len, 75.0))       # rail length along travel (Y)
carriage_len = float(PARAM(lambda: carriage_len, 30.0))  # carriage length (Y)
fit_clear = float(PARAM(lambda: fit_clear, 0.30))     # per-side sliding clearance
wall = float(PARAM(lambda: wall, 5.0))                # carriage wall / gib thickness
bolt_d = float(PARAM(lambda: bolt_d, 4.3))            # mount bolt clearance (M4 ~4.3)

# Clamp to sane ranges so extreme UI values never crash the kernel.
dovetail_w = max(10.0, min(dovetail_w, 40.0))
dovetail_ang = max(45.0, min(dovetail_ang, 75.0))
rail_h = max(6.0, min(rail_h, 20.0))
rail_len = max(30.0, min(rail_len, 200.0))
carriage_len = max(15.0, min(carriage_len, 80.0))
fit_clear = max(0.1, min(fit_clear, 0.8))
wall = max(3.0, min(wall, 12.0))
bolt_d = max(2.5, min(bolt_d, 8.0))

# A 60° optical dovetail flank sits 30° off vertical (each side). The flank runs
# out (rail_h * tan(flank_from_vert)) horizontally over the dovetail height, so
# the base is wider than the top by 2*flank_dx — the undercut that captures a gib.
_flank_from_vert = dovetail_ang / 2.0                    # 60° → 30° each side
_flank_dx = rail_h * math.tan(math.radians(_flank_from_vert))


# ── Cross-section primitives ─────────────────────────────────────────────────
def _male_dovetail_profile(top_w, height, flank_dx):
    """Male dovetail cross-section in XZ, centred on X, base at z=0. WIDER at the
    bottom (undercut) so a female channel captures it. Returns a closed wire."""
    htw = top_w / 2.0
    hbw = htw + flank_dx
    pts = [
        (-hbw, 0.0),
        (hbw, 0.0),
        (htw, height),
        (-htw, height),
    ]
    return cq.Workplane("XZ").polyline(pts).close()


def _mount_holes(body, length, width, z_top, hole_d, z_bottom=-0.5):
    """Two rows of through bolt holes down the Z axis of a base, vented top↔bottom.
    Placed along Y at ±length*0.3, on the X centreline."""
    ys = [-length * 0.3, length * 0.3] if length > 24 else [0.0]
    for y in ys:
        hole = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, y, z_bottom))
            .circle(max(0.6, hole_d / 2.0))
            .extrude(z_top - z_bottom + 1.0)
        )
        body = body.cut(hole)
    return body


# ── Part builders ────────────────────────────────────────────────────────────
def build_rail():
    """The male dovetail track: a base plinth with a 60° dovetail ridge on top,
    running the full length in Y. Mount it to a breadboard through the base bolt
    holes; carriages slide along the ridge."""
    base_h = max(4.0, rail_h * 0.55)
    base_w = dovetail_w + 2.0 * _flank_dx + 2.0 * wall

    # Base plinth (clean blank → fillet vertical edges → then cut holes).
    base = (
        cq.Workplane("XY")
        .box(base_w, rail_len, base_h, centered=(True, True, False))
    )
    try:
        base = base.edges("|Z").fillet(min(2.0, wall - 0.5))
    except Exception:
        pass

    # Dovetail ridge on top of the base, overlapping into it by 0.5 for a solid
    # weld (union of overlapping solids, not tangent).
    ridge = (
        _male_dovetail_profile(dovetail_w, rail_h, _flank_dx)
        .extrude(rail_len / 2.0, both=True)
        .translate((0, 0, base_h - 0.5))
    )
    body = base.union(ridge)

    # Mount bolt holes through the base (vented top↔bottom of the base only).
    body = _mount_holes(body, rail_len, base_w, base_h, bolt_d)
    return body


def _female_carriage_block(length):
    """A carriage block with a female 60° dovetail through-channel that captures
    the rail ridge (grown by fit_clear per side). Returns (body, body_w, body_h)."""
    ch_top_w = dovetail_w + 2.0 * fit_clear
    ch_h = rail_h + fit_clear
    ch_flank_dx = ch_h * math.tan(math.radians(_flank_from_vert))
    ch_bot_w = ch_top_w + 2.0 * ch_flank_dx

    body_w = ch_bot_w + 2.0 * wall
    body_h = ch_h + wall

    block = (
        cq.Workplane("XY")
        .box(body_w, length, body_h, centered=(True, True, False))
    )
    try:
        block = block.edges("|Z").fillet(min(2.5, wall - 0.5))
    except Exception:
        pass

    # Female channel: the SAME male dovetail profile, grown by clearance, cut
    # through both Y ends so the carriage threads onto the rail (open channel →
    # vents to outside). Sunk 0.02 below z=0 so the mouth is clean.
    chan = (
        _male_dovetail_profile(ch_top_w, ch_h + 0.5, ch_flank_dx)
        .extrude((length + 2.0) / 2.0, both=True)
        .translate((0, 0, -0.02))
    )
    body = block.cut(chan)
    return body, body_w, body_h


def build_carriage():
    """A plain sliding carriage: a female-dovetail block with a flat top platform
    carrying an M-bolt hole pattern to mount an optic, post or fixture. Slides
    freely on the rail (no lock)."""
    body, body_w, body_h = _female_carriage_block(carriage_len)

    # Optic mounting holes in the flat top: 2 holes along Y, blind-vented down to
    # the top surface (open to the top face → not trapped). Stop above the
    # channel roof so we never break into the sliding surface.
    depth = max(2.5, min(wall + 1.0, body_h - (rail_h + fit_clear) - 0.8, body_h - 1.0))
    ys = [-carriage_len * 0.25, carriage_len * 0.25] if carriage_len > 24 else [0.0]
    for y in ys:
        hole = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, y, body_h + 0.01))
            .circle(max(0.6, bolt_d / 2.0))
            .extrude(-(depth + 0.01))
        )
        body = body.cut(hole)
    return body


def build_clamp():
    """A locking carriage: like the carriage but with a gib slit down one side and
    a cross clamp screw. Tightening the screw closes the slit so the female
    dovetail pinches the rail flanks and locks the slide in place."""
    body, body_w, body_h = _female_carriage_block(carriage_len)
    ch_h = rail_h + fit_clear

    # Gib slit: a thin through-slot from the +X outer wall inward toward the
    # channel, running the full length (Y), at mid-height of the channel. This
    # lets the outer jaw flex when the cross screw is tightened.
    slit_x = body_w / 2.0 - wall * 0.5
    slit = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(slit_x, 0, ch_h * 0.5))
        .box(1.6, carriage_len + 2.0, ch_h * 0.9, centered=(True, True, True))
    )
    body = body.cut(slit)

    # Cross clamp screw across X, above the channel, through the flexing jaw.
    scr_z = ch_h + (body_h - ch_h) * 0.5
    screw = (
        cq.Workplane("YZ")
        .transformed(offset=cq.Vector(0, scr_z, 0))
        .circle(max(0.6, bolt_d / 2.0))
        .extrude(body_w / 2.0 + 1.0, both=True)
    )
    body = body.cut(screw)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "carriage":
    result = build_carriage()
elif target_part == "clamp":
    result = build_clamp()
else:
    result = build_rail()
