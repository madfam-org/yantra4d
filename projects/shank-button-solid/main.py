"""
Button — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The printable solid button. Fashion Cabinet's `shank-button` notion owns the
fashion semantics — ligne sizing and the placket placement guide — and bridges to
THIS solid for the hardware. Sized in ligne (1 L = 0.635 mm, the button trade's
unit): the manifest maps `diameter_mm = button_ligne * 0.635`, so the same ligne
that lays out a Fashion Cabinet placket makes the matching button here.

Modes (dispatched via `target_part`):
  * "shank"      — a domed button with a closed shank loop on the back (no face
                   holes); the loop is what thread passes through. One solid.
  * "sew_through" — a flat button with a rim and 2 or 4 sew holes through the face.
  * "toggle"     — a barrel toggle (duffle-coat closure) with a transverse thread
                   channel.

Every part is a watertight solid. Holes and channels are cut clean through
(extended past both faces) so nothing leaves a coincident face.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `diameter_mm`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr.
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
diameter_mm = float(PARAM(lambda: diameter_mm, 15.24))   # button diameter (24 L default)
thickness   = float(PARAM(lambda: thickness,    3.2))    # button body thickness (mm)
holes       = int(  PARAM(lambda: holes,        4))      # sew-through hole count (2 or 4)
hole_dia    = float(PARAM(lambda: hole_dia,     1.6))    # sew hole / shank bore diameter (mm)
rim         = float(PARAM(lambda: rim,          0.8))    # raised rim height on sew-through (mm)

target_part = str(  PARAM(lambda: target_part, "shank"))  # shank|sew_through|toggle

# ── Safe clamps ──────────────────────────────────────────────────────────────
diameter_mm = max(6.0, min(diameter_mm, 60.0))
thickness   = max(1.5, min(thickness, 12.0))
hole_dia    = max(0.8, min(hole_dia, 4.0))
rim         = max(0.0, min(rim, 2.0))
holes       = 2 if holes <= 2 else 4

R = diameter_mm / 2.0


# ── Part builders ─────────────────────────────────────────────────────────────
def build_shank():
    """A domed button with a closed shank loop on the back. The dome is a spherical
    cap; the shank is a short pedestal carrying a ring (a small torus) whose bore
    the thread passes through. One watertight solid, face up (+Z)."""
    # Domed body: a cylinder with a filleted top edge approximates the dome and
    # stays boolean-robust (a true cap via intersection is heavier and can fail on
    # thin buttons).
    body = cq.Workplane("XY").circle(R).extrude(thickness)
    try:
        body = body.faces(">Z").edges().fillet(min(thickness * 0.9, R * 0.6))
    except Exception:
        pass

    # Shank pedestal on the back (-Z), then a ring for the thread.
    ped_h = max(1.2, thickness * 0.5)
    ring_r = max(hole_dia, R * 0.28)        # ring centreline radius
    tube_r = max(0.6, hole_dia * 0.5)       # ring tube (also sets the bore wall)
    pedestal = (
        cq.Workplane("XY")
        .circle(ring_r * 0.9)
        .extrude(-ped_h)
        .translate((0, 0, 0.2))             # overlap into the body for a solid fuse
    )
    # Ring lying in a vertical plane (bore axis along X) below the pedestal.
    ring = cq.Solid.makeTorus(
        ring_r, tube_r,
        pnt=cq.Vector(0, 0, -ped_h - ring_r * 0.2),
        dir=cq.Vector(1, 0, 0),
    )
    body = body.union(pedestal).union(cq.Workplane(obj=ring))
    return body


def build_sew_through():
    """A flat sew-through button: a disc with a slightly raised rim, a shallow
    central bowl, and 2 or 4 sew holes through the face. One watertight solid."""
    body = cq.Workplane("XY").circle(R).extrude(thickness)
    # Raised rim: a thin ring proud of the top face.
    if rim > 0.05:
        rim_ring = (
            cq.Workplane("XY")
            .circle(R)
            .circle(R - max(0.8, R * 0.12))
            .extrude(rim)
            .translate((0, 0, thickness - 0.01))
        )
        body = body.union(rim_ring)
    # Shallow central bowl (the thread well) on the top face.
    bowl_r = R * 0.55
    bowl = (
        cq.Workplane("XY")
        .circle(bowl_r)
        .extrude(-max(0.4, thickness * 0.2))
        .translate((0, 0, thickness + rim + 0.01))
    )
    body = body.cut(bowl)
    # Sew holes on a bolt circle.
    hbc = R * 0.32                       # hole bolt-circle radius
    positions = ([(-hbc, 0), (hbc, 0)] if holes == 2
                 else [(-hbc, -hbc), (hbc, -hbc), (-hbc, hbc), (hbc, hbc)])
    for hx, hy in positions:
        hole = (
            cq.Workplane("XY")
            .center(hx, hy)
            .circle(hole_dia / 2.0)
            .extrude(thickness + rim + 4.0)
            .translate((0, 0, -2.0))
        )
        body = body.cut(hole)
    return body


def build_toggle():
    """A barrel toggle (duffle-coat closure): a rounded cylinder standing along X
    with a transverse thread channel near one end. One watertight solid."""
    length = diameter_mm            # reuse diameter as toggle length
    r = max(3.0, thickness * 0.9)   # barrel radius from thickness
    barrel = (
        cq.Workplane("YZ")
        .circle(r)
        .extrude(length, both=False)
        .translate((-length / 2.0, 0, 0))
    )
    try:
        barrel = barrel.faces("<X or >X").fillet(r * 0.4)
    except Exception:
        pass
    # Transverse thread channel (through Y) near the centre.
    channel = (
        cq.Workplane("XZ")
        .center(0, 0)
        .circle(hole_dia / 2.0)
        .extrude(2 * r + 4.0)
        .translate((0, -(r + 2.0), 0))
    )
    barrel = barrel.cut(channel)
    return barrel


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "sew_through":
    result = build_sew_through()
elif target_part == "toggle":
    result = build_toggle()
else:
    result = build_shank()
