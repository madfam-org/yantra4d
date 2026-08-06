"""
Vent Louvre — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Airflow deflectors and vent inserts: a rectangular frame spanned by a bank of
angled blades that steer or diffuse air. Three modes:

  * "louvre_insert" — a flat framed louvre grille that drops into a vent opening,
                      blades fixed at a set angle.
  * "deflector"     — a louvre on a protruding hood/scoop that throws air away
                      from a surface (e.g. off a laptop, out of a footwell).
  * "grille"        — a fine straight-slat grille (many thin blades) for a
                      cover/intake screen.

The angled blade profile is the Common Denominator Geometry — all three modes are
the same solid-blade-in-frame construction, sized by the opening and blade count.
Every blade is a solid unioned bar, so the part stays watertight.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `open_w`).
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


# ── Parameters ───────────────────────────────────────────────────────────────
open_w       = float(PARAM(lambda: open_w,       80.0))   # opening width (X)
open_h       = float(PARAM(lambda: open_h,       50.0))   # opening height (Y)
frame_w      = float(PARAM(lambda: frame_w,       5.0))   # frame border width
depth        = float(PARAM(lambda: depth,        10.0))   # frame / blade depth (Z)
blade_count  = int(  PARAM(lambda: blade_count,     6))   # number of blades
blade_angle  = float(PARAM(lambda: blade_angle,  35.0))   # blade tilt from vertical (deg)
blade_thick  = float(PARAM(lambda: blade_thick,   2.0))   # blade thickness
rim_lip      = float(PARAM(lambda: rim_lip,       2.0))   # front lip that locates the insert
hood_len     = float(PARAM(lambda: hood_len,     22.0))   # deflector hood projection (Y)

target_part  = str(  PARAM(lambda: target_part, "louvre_insert"))
# "louvre_insert" | "deflector" | "grille"


# ── Derived / clamped geometry ───────────────────────────────────────────────
open_w = max(20.0, open_w)
open_h = max(15.0, open_h)
frame_w = max(2.0, frame_w)
depth = max(4.0, depth)
blade_thick = max(1.0, min(blade_thick, depth - 1.0))
ow = open_w + 2.0 * frame_w
oh = open_h + 2.0 * frame_w


# ── Shared helper: rectangular frame ─────────────────────────────────────────
def rect_frame(w, d, h, opening_w, opening_h):
    """A rectangular frame (border ring): outer block minus an inner through-
    window. Base at z=0. Watertight."""
    outer = (
        cq.Workplane("XY")
        .box(w, d, h, centered=(True, True, False))
    )
    window = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -1.0))
        .box(opening_w, opening_h, h + 2.0, centered=(True, True, False))
    )
    return outer.cut(window)


def _blade_bank(n, angle_deg, thick, span_w, span_h, z0, dz):
    """Bank of `n` angled blades filling a span_w × span_h opening, each blade a
    solid bar of thickness `thick` tilted `angle_deg` about the X axis, unioned
    then intersected with the opening prism so nothing pokes out of the frame.

    Returns a single watertight solid (or None if degenerate)."""
    if n < 1:
        return None
    ang = max(0.0, min(angle_deg, 75.0))
    # Blades run full-width (X); they are spaced along Y and tilted about X.
    pitch = span_h / n
    blade_len_y = pitch + thick  # overlap so tilted blades overlap in projection
    bank = None
    for i in range(n):
        yc = -span_h / 2.0 + (i + 0.5) * pitch
        blade = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, yc, z0 + dz / 2.0))
            .transformed(rotate=cq.Vector(ang, 0, 0))
            .box(span_w + 4.0, blade_len_y, thick, centered=(True, True, True))
        )
        bank = blade if bank is None else bank.union(blade)
    if bank is None:
        return None
    # Clip to the opening so tilted ends don't protrude past the frame walls.
    clip = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z0 - 0.5))
        .box(span_w, span_h, dz + 1.0, centered=(True, True, False))
    )
    return bank.intersect(clip)


# ── louvre_insert ─────────────────────────────────────────────────────────────
def build_louvre_insert():
    """A framed louvre that drops into a vent opening, with a front locating lip
    around the border."""
    frame = rect_frame(ow, oh, depth, open_w, open_h)

    blades = _blade_bank(blade_count, blade_angle, blade_thick,
                         open_w, open_h, 0.0, depth)
    body = frame if blades is None else frame.union(blades)

    # Front locating lip: a thin wider ring on the front face.
    if rim_lip > 0.05:
        lip = rect_frame(ow + 2.0 * rim_lip, oh + 2.0 * rim_lip, rim_lip,
                         open_w, open_h)
        lip = lip.translate((0, 0, depth))
        body = body.union(lip)
    return body


# ── deflector ─────────────────────────────────────────────────────────────────
def build_deflector():
    """A louvre on a protruding hood: the framed louvre plus angled side/top
    walls forming a scoop that throws air in the blade direction."""
    body = build_louvre_insert()

    # Hood: three walls (top + two sides) projecting forward (+Z... use +Y as the
    # throw direction is set by the blades). Build a shallow open box on the front
    # and cut its inner cavity, leaving walls.
    hood = max(6.0, hood_len)
    outer = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, depth))
        .box(ow, oh, hood, centered=(True, True, False))
    )
    inner = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -frame_w, depth - 1.0))
        .box(open_w, oh, hood + 2.0, centered=(True, True, False))
    )
    hood_walls = outer.cut(inner)
    # Open the bottom (−Y) so the scoop mouth faces down/out.
    mouth = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -oh / 2.0, depth + hood / 2.0))
        .box(open_w, frame_w * 3.0, hood, centered=(True, True, True))
    )
    hood_walls = hood_walls.cut(mouth)
    return body.union(hood_walls)


# ── grille ────────────────────────────────────────────────────────────────────
def build_grille():
    """A fine straight-slat grille: a frame filled with many thin vertical bars
    (angle forced near 0) for a cover / intake screen."""
    frame = rect_frame(ow, oh, depth, open_w, open_h)

    # Many thin blades, straight (small angle), denser than a louvre.
    n = max(blade_count, 8)
    blades = _blade_bank(n, min(blade_angle, 8.0), max(1.0, blade_thick * 0.8),
                         open_w, open_h, 0.0, depth)
    body = frame if blades is None else frame.union(blades)

    # Add a couple of cross bars (X-direction ribs) for stiffness.
    ribs = max(0, min(2, n // 4))
    if ribs > 0:
        step = open_w / (ribs + 1)
        for i in range(1, ribs + 1):
            x = -open_w / 2.0 + i * step
            rib = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(x, 0, 0))
                .box(max(1.0, blade_thick), open_h, depth,
                     centered=(True, True, False))
            )
            body = body.union(rib)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "deflector":
    result = build_deflector()
elif target_part == "grille":
    result = build_grille()
else:  # "louvre_insert"
    result = build_louvre_insert()
