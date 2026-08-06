"""
Capo / Slide (parametric) — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A capo clamps across the fretboard to raise the pitch of every string. The
functional interface is the fretboard RADIUS — the contact bar's face is a
concave cylinder matched to the neck's crown so it presses every string evenly.
Real fretboard radii: 7.25 in (184 mm, vintage Fender), 9.5 in (241 mm, modern
Fender), 12 in (305 mm, Gibson), 16 in (406 mm, flat-ish), classical ≈ flat.

Modes:
  - yoke_capo    : a C-yoke that hooks over the neck with a thumbscrew boss; the
    screw drives a radiused pad bar down onto the strings (screw-tension capo).
  - lever_capo   : a trigger-style body with a radiused pad and a slot for a
    band/spring that snaps the capo shut (quick-change capo).
  - partial_capo : a short capo bar covering only some strings (drop/partial
    tunings), radiused to the same neck.

Watertight strategy:
  The radiused pad face is a concave cylinder CUT from the bar underside — the
  cylinder axis runs along the bar so the contact face is an arc (open to the
  outside, not a cavity). The yoke is an extruded C-profile (a rounded-rect with
  a neck window open on one side → not enclosed). Screw holes are through-holes.
  Blanks fillet-cleaned BEFORE feature cuts. No trapped voids.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` pre-injected; params arrive as bare globals.
  - Read each via PARAM(lambda: name, default). No globals()/eval/getattr.
  - Assign the final solid to `result`.
"""

import cadquery as cq


def PARAM(getter, default):
    """Injected global if present else default; `except` catches the unbound-name
    NameError the sandbox raises (globals()/NameError are hidden)."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Fretboard radius presets (mm) ────────────────────────────────────────────
RADIUS_STD = {
    "7.25in": 184.0,
    "9.5in":  241.0,
    "12in":   305.0,
    "16in":   406.0,
    "flat":   2000.0,   # classical / near-flat (a very large radius reads flat)
}


def radius_geo(name):
    return RADIUS_STD.get(name, RADIUS_STD["9.5in"])


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "yoke_capo"))
# "yoke_capo" | "lever_capo" | "partial_capo"

fret_radius = str(PARAM(lambda: fret_radius, "9.5in"))   # fretboard radius preset
neck_w      = float(PARAM(lambda: neck_w, 46.0))         # fretboard width at the capo (mm)
neck_th     = float(PARAM(lambda: neck_th, 22.0))        # neck front-to-back thickness (mm)
pad_w       = float(PARAM(lambda: pad_w, 10.0))          # pad bar width along the string run (mm)
strings     = int(PARAM(lambda: strings, 6))             # strings the capo covers
screw_d     = float(PARAM(lambda: screw_d, 5.2))         # tension screw hole (M5) (mm)
wall        = float(PARAM(lambda: wall, 6.0))            # yoke / body wall (mm)

# Clamp to sane ranges so extreme UI values still build watertight.
fret_radius = fret_radius if fret_radius in RADIUS_STD else "9.5in"
neck_w  = max(38.0, min(neck_w, 60.0))
neck_th = max(15.0, min(neck_th, 30.0))
pad_w   = max(6.0, min(pad_w, 18.0))
strings = max(1, min(strings, 8))
screw_d = max(2.5, min(screw_d, 8.0))
wall    = max(4.0, min(wall, 10.0))

_R = radius_geo(fret_radius)
_string_pitch = neck_w / max(1, (6 - 1))   # ~ nut string spacing (6-string reference)
_cover_w = min(neck_w + 6.0, _string_pitch * (strings - 1) + 12.0) if strings > 1 else 14.0


# ── Helpers (inlined) ─────────────────────────────────────────────────────────
def _radiused_pad(length, width, height, radius):
    """A pad bar whose BOTTOM face is a shallow concave cylinder (radius) so it
    matches a fretboard crown. The cutting cylinder's axis runs along X (the
    neck-width direction).

    Geometry: the crescent removed from the underside has depth = the sagitta
    s = R - sqrt(R^2 - (w/2)^2) at the centre and 0 at the y-edges. For the arc
    to pass through both bottom edges (y=+/-w/2, z=0) and dip up to (y=0, z=s),
    the cylinder centre sits at world z = s - R (well below the bar). This leaves
    an arc contact face open to the outside — never a sealed cavity."""
    bar = cq.Workplane("XY").box(length, width, height, centered=(True, True, False))
    half_w = width / 2.0
    # Guard the sqrt for width >= 2R (never true here, but stay safe).
    inner = max(0.0, radius * radius - half_w * half_w)
    sag = radius - (inner ** 0.5)
    z_center = sag - radius
    # Build a cylinder axis-aligned to X: a circle on XZ won't rotate correctly,
    # so make a Y-axis... use makeCylinder along X via a solid primitive.
    cyl = cq.Solid.makeCylinder(
        radius, length + 4.0,
        pnt=cq.Vector(-(length / 2.0) - 2.0, 0, z_center),
        dir=cq.Vector(1, 0, 0),
    )
    bar = bar.cut(cq.Workplane(obj=cyl))
    try:
        bar = bar.edges("|X and >Z").fillet(min(width * 0.2, 1.5))
    except Exception:
        pass
    return bar


# ── Part builders ────────────────────────────────────────────────────────────
def build_yoke_capo():
    """A C-yoke that hooks over the neck: a solid top bridge (carries the
    thumbscrew) and two side walls that hug the neck, open at the bottom so the
    neck slots up in. A radiused pad on the underside of the bridge presses the
    strings. Built as ONE solid: a full block minus an open-bottom neck window,
    so the bridge and both walls stay connected (never severed)."""
    span = neck_w + 2.0 * wall
    top_bridge = wall + 3.0            # solid top thickness (carries the screw)
    depth = neck_th + top_bridge + 4.0
    yoke = cq.Workplane("XY").box(span, pad_w + 4.0, depth, centered=(True, True, False))
    try:
        yoke = yoke.edges("|Y").fillet(3.0)
    except Exception:
        pass
    # Neck window: open at the BOTTOM (z=0), rising to just under the top bridge,
    # leaving two side walls + a solid top bridge (a C-section, never enclosed).
    win_h = depth - top_bridge
    win = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -1.0))
        .box(neck_w, pad_w + 6.0, win_h + 1.0, centered=(True, True, False))
    )
    yoke = yoke.cut(win)

    # Radiused pad on the underside of the top bridge (its scooped face points
    # DOWN toward the neck). Seat it up INTO the bridge by 1 mm so it fuses.
    pad = _radiused_pad(neck_w - 0.5, pad_w, wall + 3.0, _R)
    pad = pad.translate((0, 0, win_h - 1.0))
    body = yoke.union(pad)

    # Thumbscrew hole down through the top bridge (through-hole, vented) so a
    # screw can tension the neck against the pad.
    screw = (
        cq.Workplane("XY")
        .circle(screw_d / 2.0)
        .extrude(top_bridge + 4.0)
        .translate((0, 0, depth - top_bridge - 2.0))
    )
    body = body.cut(screw)
    return body


def build_lever_capo():
    """A trigger/quick-change body: a radiused pad on a spine, with a slot for a
    rubber band or spring at the back that snaps the capo shut on the neck."""
    spine_h = neck_th + wall + 8.0
    spine = cq.Workplane("XY").box(pad_w + 4.0, wall + 2.0, spine_h, centered=(True, True, False))
    try:
        spine = spine.edges("|Y").fillet(2.5)
    except Exception:
        pass

    # Radiused pad reaching across the neck (length spans X = neck width) at the
    # top, pressing down onto the strings.
    pad = _radiused_pad(neck_w, pad_w, wall + 3.0, _R).translate((0, 0, spine_h - (wall + 3.0)))
    body = spine.union(pad)

    # A back arm with a band slot (obround through-slot, vented) for the spring.
    arm = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -(wall + 2.0) / 2.0 - 6.0, spine_h * 0.3))
        .box(pad_w + 4.0, 12.0, wall + 2.0, centered=(True, True, False))
    )
    body = body.union(arm)
    band = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, spine_h * 0.3 + (wall + 2.0) / 2.0, -(wall + 2.0) - 6.0))
        .slot2D(pad_w * 0.6, 3.0, angle=90)
        .extrude(20.0, both=True)
    )
    body = body.cut(band)
    return body


def build_partial_capo():
    """A short capo bar covering only some strings (drop / partial tunings),
    radiused to the same neck, with a band slot each end to strap it on."""
    length = _cover_w
    pad = _radiused_pad(length, pad_w + 2.0, wall + 4.0, _R)

    # A low spine behind the pad for stiffness and to carry the band slots.
    spine = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, wall + 2.0))
        .box(length, pad_w + 6.0, wall, centered=(True, True, False))
    )
    body = pad.union(spine)

    # Band holes near each end: clean vertical through-holes down through the
    # spine (open top and bottom → vented), for a strap/band that holds the
    # partial capo on. Two holes in one pushPoints cut = one boolean.
    hole_pts = [(-(length / 2.0 - 5.0), 0.0), (length / 2.0 - 5.0, 0.0)]
    holes = (
        cq.Workplane("XY")
        .pushPoints(hole_pts)
        .circle(1.6)
        .extrude(wall * 3.0 + 8.0)
        .translate((0, 0, -1.0))
    )
    body = body.cut(holes)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "lever_capo":
    result = build_lever_capo()
elif target_part == "partial_capo":
    result = build_partial_capo()
else:
    result = build_yoke_capo()
