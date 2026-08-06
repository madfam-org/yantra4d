"""
Magnetic Coupling Hub — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A contactless magnetic shaft coupling: two hubs each carry a ring of disc magnets;
placed face to face (or across a thin non-magnetic barrier) they lock magnetically
and transmit torque with NO physical connection — so one shaft can drive another
through a sealed wall (pumps, stirrers, robots) or slip harmlessly on overload.

Each part is a PRINTABLE SINGLE-BODY solid. Magnet pockets are blind bores that
open to ONE face (the coupling face) — vented to outside, no trapped void, so the
whole mesh is watertight. Drop in disc magnets and glue.

It grows the shaft-spline family: the hub's shaft bore supports a round or D-flat
6/8 mm shaft with a set-screw — the SAME shaft interface as `knob-dshaft`, so a
magnetic hub fits any shaft a knob-dshaft fits.

Modes:
  - coupling_hub : the driving/driven hub — a disc with a shaft bore (round or
                   D-flat), a set-screw, and a ring of N disc-magnet pockets.
  - disc_rotor   : a thinner magnet-carrier disc (no hub boss) for a pancake /
                   axial coupling or an encoder magnet ring.
  - cup_shell    : a cup-shaped shell that houses the opposing hub across a wall
                   — the outer half of a sealed (through-barrier) coupling.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `target_part`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use
    globals()/eval/getattr — they are not in the sandbox's allowed builtins.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq
import math


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "coupling_hub"))
# "coupling_hub" | "disc_rotor" | "cup_shell"

hub_d = float(PARAM(lambda: hub_d, 36.0))         # coupling disc outer diameter
hub_h = float(PARAM(lambda: hub_h, 16.0))         # hub height
shaft_dia = float(PARAM(lambda: shaft_dia, 6.0))  # shaft bore diameter (6 or 8 mm)
bore_type = str(PARAM(lambda: bore_type, "D-flat"))  # "round" | "D-flat"
flat_depth = float(PARAM(lambda: flat_depth, 0.5))   # D-flat depth into the bore
setscrew_dia = float(PARAM(lambda: setscrew_dia, 3.2))  # M3 set-screw
n_magnets = int(PARAM(lambda: n_magnets, 6))      # disc magnets in the ring
magnet_d = float(PARAM(lambda: magnet_d, 8.0))    # disc-magnet diameter
magnet_h = float(PARAM(lambda: magnet_h, 3.0))    # disc-magnet thickness

# ── Clamp to sane ranges ─────────────────────────────────────────────────────
hub_d = max(18.0, min(hub_d, 80.0))
hub_h = max(6.0, min(hub_h, 30.0))
shaft_dia = max(2.0, min(shaft_dia, 12.0))
flat_depth = max(0.0, min(flat_depth, 3.0))
setscrew_dia = max(2.0, min(setscrew_dia, 5.0))
n_magnets = max(2, min(n_magnets, 12))
magnet_d = max(3.0, min(magnet_d, 16.0))
magnet_h = max(1.5, min(magnet_h, 8.0))

# magnet ring radius so magnets fit inside the disc rim
magnet_bc = max(magnet_d / 2.0 + 1.0, hub_d / 2.0 - magnet_d / 2.0 - 2.0)


# ── Helpers ──────────────────────────────────────────────────────────────────
def _dflat(body, z0, depth):
    """Mill a D-flat chord off a shaft bore already cut at the origin: a box whose
    inner face sits `flat_depth` inside the bore wall. No-op for a round bore."""
    if bore_type != "D-flat" or flat_depth <= 0.0:
        return body
    off = shaft_dia - flat_depth
    flat = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(off, 0, z0))
        .box(shaft_dia, shaft_dia * 1.5, depth + 1.0, centered=(True, True, False))
    )
    return body.cut(flat)


def _magnet_ring(body, face_z, into_z):
    """Cut N blind disc-magnet pockets on a bolt circle, opening to the coupling
    face at z=face_z and going DOWN to z=into_z (open to the face → vented, no
    trapped void)."""
    depth = face_z - into_z
    for i in range(n_magnets):
        a = math.radians(360.0 * i / n_magnets)
        cx = magnet_bc * math.cos(a)
        cy = magnet_bc * math.sin(a)
        pocket = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(cx, cy, into_z))
            .circle(magnet_d / 2.0 + 0.15)
            .extrude(depth + 0.5)   # pops through the face → open pocket
        )
        body = body.cut(pocket)
    return body


def build_coupling_hub():
    """The driving/driven hub: a disc with a shaft bore (round or D-flat) + set-
    screw and a ring of N disc-magnet pockets on the coupling face (top)."""
    ro = hub_d / 2.0
    body = cq.Workplane("XY").circle(ro).extrude(hub_h)
    try:
        body = body.edges(">Z").fillet(min(1.5, ro * 0.1))
    except Exception:
        pass
    # magnet pockets on the top (coupling) face
    body = _magnet_ring(body, face_z=hub_h, into_z=hub_h - magnet_h - 0.3)
    # shaft bore up from the bottom face... cut DOWN from top but stop above the
    # magnet pockets so they don't collide. Bore depth = most of the hub.
    bore_depth = min(hub_h - magnet_h - 1.5, hub_h * 0.7)
    bore_depth = max(3.0, bore_depth)
    # bore opens on the BOTTOM face → build it from the bottom.
    z0 = -0.5
    bore = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z0))
        .circle(shaft_dia / 2.0)
        .extrude(bore_depth + 0.5)
    )
    body = body.cut(bore)
    body = _dflat(body, z0, bore_depth)
    # radial set-screw through the rim into the bore
    ss_z = bore_depth * 0.5
    ss = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, ss_z, ro - 1.0))
        .circle(setscrew_dia / 2.0)
        .extrude(ro - shaft_dia / 2.0 + 1.0)
    )
    body = body.cut(ss)
    return body


def build_disc_rotor():
    """A thinner magnet-carrier disc (pancake / axial coupling face or encoder
    magnet ring): a low disc with a central shaft bore (through) and a ring of
    magnet pockets on the top face."""
    ro = hub_d / 2.0
    disc_h = max(magnet_h + 2.0, hub_h * 0.4)
    body = cq.Workplane("XY").circle(ro).extrude(disc_h)
    try:
        body = body.edges(">Z or <Z").fillet(min(1.0, disc_h * 0.2))
    except Exception:
        pass
    # magnet pockets on top face
    body = _magnet_ring(body, face_z=disc_h, into_z=disc_h - magnet_h - 0.3)
    # central through shaft bore (vented both ends)
    bore = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -0.5))
        .circle(shaft_dia / 2.0)
        .extrude(disc_h + 1.0)
    )
    body = body.cut(bore)
    body = _dflat(body, -0.5, disc_h)
    return body


def build_cup_shell():
    """A cup-shaped shell housing the opposing hub across a thin wall — the outer
    half of a sealed (through-barrier) coupling. A cup: solid disc base carrying
    the magnet ring on its INNER floor, with an upstanding rim wall around a bore
    that clears the driven hub. The recess opens to the top face → no trapped void.
    """
    ro = hub_d / 2.0
    rim = 3.0
    base_t = magnet_h + 2.5
    body = cq.Workplane("XY").circle(ro).extrude(hub_h)
    # inner recess (open to the top face) that the opposing hub sits in
    recess = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, base_t))
        .circle(ro - rim)
        .extrude(hub_h)   # pops out the top → open recess (vented)
    )
    body = body.cut(recess)
    # magnet pockets on the inner floor (open UP into the recess → vented)
    body = _magnet_ring(body, face_z=base_t, into_z=base_t - magnet_h - 0.3)
    # central shaft bore through the base (vents recess → bottom)
    bore = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -0.5))
        .circle(shaft_dia / 2.0)
        .extrude(base_t + 1.0)
    )
    body = body.cut(bore)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "disc_rotor":
    result = build_disc_rotor()
elif target_part == "cup_shell":
    result = build_cup_shell()
else:
    result = build_coupling_hub()
