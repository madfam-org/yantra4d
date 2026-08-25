"""
Peristaltic Pump Rotor — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The rotating core of a peristaltic (roller) pump: a rotor carries N rollers that
squeeze a flexible tube against a curved race, pushing fluid along without the
pump ever touching it (ideal for lab dosing, aquaria, food, chemistry). This
cartridge builds the rotor, the tube race (housing), and a single roller as
PRINTABLE SINGLE-BODY solids sized for standard 3/16 in (4.76 mm) and 1/4 in
(6.35 mm) OD silicone tubing.

Modes:
  - rotor      : the roller-carrier disc with a central drive-shaft bore (D-flat
                 or set-screw) and N roller pin bosses on a bolt circle.
  - tube_race  : the semicircular pump race — a housing block with a curved
                 channel that cradles the tube at the roller squeeze radius, with
                 tube entry/exit ports and mounting holes.
  - roller     : a single roller (a grooved cylinder with a pin bore) that rolls
                 on the rotor pins and pinches the tube.

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


# ── Tube standards ───────────────────────────────────────────────────────────
# nominal OD (mm) for common peristaltic tubing sizes.
TUBE_TABLE = {"3/16in": 4.76, "1/4in": 6.35}


def tube_od(kind):
    return TUBE_TABLE.get(kind, 6.35)


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "rotor"))
# "rotor" | "tube_race" | "roller"

tube = str(PARAM(lambda: tube, "1/4in"))          # tubing size
rotor_d = float(PARAM(lambda: rotor_d, 50.0))     # rotor outer diameter
n_rollers = int(PARAM(lambda: n_rollers, 3))      # number of rollers
rotor_h = float(PARAM(lambda: rotor_h, 16.0))     # rotor / roller height
shaft_d = float(PARAM(lambda: shaft_d, 6.0))      # drive-shaft bore
roller_d = float(PARAM(lambda: roller_d, 12.0))   # roller outer diameter
pin_d = float(PARAM(lambda: pin_d, 4.0))          # roller pin diameter
wall = float(PARAM(lambda: wall, 4.0))            # race wall thickness

# ── Clamp to sane ranges ─────────────────────────────────────────────────────
rotor_d = max(30.0, min(rotor_d, 90.0))
n_rollers = max(2, min(n_rollers, 5))
rotor_h = max(8.0, min(rotor_h, 30.0))
shaft_d = max(3.0, min(shaft_d, 12.0))
roller_d = max(8.0, min(roller_d, 20.0))
pin_d = max(2.0, min(pin_d, 8.0))
wall = max(2.5, min(wall, 8.0))

t_od = tube_od(tube)
# roller pin bolt circle radius so a roller at radius pin_bc + roller_d/2 reaches
# the squeeze radius. Keep the rollers inside the rotor.
pin_bc = rotor_d / 2.0 - roller_d / 2.0 - 2.0
# occlusion (squeeze) radius: where the tube is pinched flat between roller & race
squeeze_r = pin_bc + roller_d / 2.0 + t_od * 0.15


# ── Rotor ────────────────────────────────────────────────────────────────────
def build_rotor():
    """The roller-carrier disc: a hub disc with a central shaft bore (D-flat), a
    set-screw hole, and N roller-pin bosses on a bolt circle. Single solid: the
    disc + bosses unioned, then bores cut (all vented to faces)."""
    ro = rotor_d / 2.0
    disc = cq.Workplane("XY").circle(ro).extrude(rotor_h)
    body = disc

    # Roller pockets: cut N slots so each roller sits in a fork; keep it simple —
    # instead cut cylindrical clearance pockets for the rollers around the rim.
    for i in range(n_rollers):
        a = 360.0 * i / n_rollers
        rad = math.radians(a)
        cx = pin_bc * math.cos(rad)
        cy = pin_bc * math.sin(rad)
        # roller clearance pocket (open to top and rim → vented)
        pocket = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(cx, cy, wall))
            .circle(roller_d / 2.0 + 0.6)
            .extrude(rotor_h)
        )
        body = body.cut(pocket)
        # roller pin bore (through Z, vented both ends)
        pin_bore = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(cx, cy, -1.0))
            .circle(pin_d / 2.0)
            .extrude(rotor_h + 2.0)
        )
        body = body.cut(pin_bore)

    # Central drive-shaft bore with a D-flat (through, vented both ends).
    shaft = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -1.0))
        .circle(shaft_d / 2.0)
        .extrude(rotor_h + 2.0)
    )
    body = body.cut(shaft)
    # D-flat: chop a chord off the bore
    flat = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(shaft_d * 0.42, 0, -1.0))
        .box(shaft_d, shaft_d, rotor_h + 2.0, centered=(True, True, False))
    )
    body = body.cut(flat)
    # set-screw hole radially into the hub down to the shaft bore (vented rim→bore)
    setscrew = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, rotor_h / 2.0, ro - 1.0))
        .circle(1.4)
        .extrude(ro - shaft_d / 2.0 + 1.0)
    )
    body = body.cut(setscrew)
    return body


def build_tube_race():
    """The pump race: a housing block with a semicircular channel that cradles the
    tube at the squeeze radius, plus tube entry/exit ports and corner mounting
    holes. Single solid: block filleted first, then the arc channel + ports cut.

    The channel is built as the difference of two concentric revolved rings (an
    annular groove open to the top face) → vents to outside, no trapped void, and
    avoids the revolve-of-a-cut-profile trap by revolving FILLED rings and
    subtracting them as tools."""
    outer_r = squeeze_r + t_od / 2.0 + wall
    block_w = 2.0 * outer_r + 2.0 * wall
    block_h = t_od + 2.0 * wall
    block = (
        cq.Workplane("XY")
        .box(block_w, block_w, block_h, centered=(True, True, False))
    )
    try:
        block = block.edges("|Z").fillet(4.0)
    except Exception:
        pass
    body = block

    # Semicircular tube channel: a toroidal groove at radius squeeze_r about the
    # Z (spin) axis, cut into the block. Built with makeTorus (a clean filled
    # torus tool) rather than a revolved cut profile — this avoids the
    # revolve-of-a-cut trap and the axis-ambiguity of Workplane.revolve. The
    # groove sits near the top face and the tube ports (below) open it to outside.
    ch_r = t_od / 2.0 + 0.3
    torus = cq.Solid.makeTorus(squeeze_r, ch_r)
    groove_tool = cq.Workplane("XY").add(torus).translate((0, 0, block_h - ch_r + 0.5))
    body = body.cut(groove_tool)

    # Cut the block down to a HALF race (180°): remove the -X half so the tube
    # wraps a semicircle. Keep +X half.
    half_cut = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(-block_w / 2.0, 0, -1.0))
        .box(block_w, block_w + 2.0, block_h + 2.0, centered=(True, True, False))
    )
    body = body.cut(half_cut)

    # Tube entry & exit ports: horizontal bores in +Y and -Y faces meeting the
    # groove ends (vented outside → groove).
    for sy in (-1, 1):
        port = (
            cq.Workplane("XZ")
            .transformed(offset=cq.Vector(squeeze_r, block_h - ch_r + 0.5, 0))
            .circle(t_od / 2.0 + 0.3)
            .extrude(sy * (block_w / 2.0 + 2.0))
        )
        body = body.cut(port)

    # Corner mounting holes (through Z, vented).
    mh = outer_r * 0.72
    for (sx, sy) in ((1, 1), (1, -1)):
        hole = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(sx * mh, sy * mh, -1.0))
            .circle(1.7)   # M3 clearance
            .extrude(block_h + 2.0)
        )
        body = body.cut(hole)
    return body


def build_roller():
    """A single roller: a cylinder with slightly crowned ends (a grooved barrel)
    and a central pin bore. Rolls on a rotor pin and pinches the tube."""
    rr = roller_d / 2.0
    body = cq.Workplane("XY").circle(rr).extrude(rotor_h)
    # chamfer both ends so it doesn't dig into the tube (fillet blank BEFORE bore)
    try:
        body = body.edges(">Z or <Z").fillet(min(1.5, rr * 0.3))
    except Exception:
        pass
    # central pin bore (through, vented both ends)
    bore = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -1.0))
        .circle(pin_d / 2.0 + 0.3)
        .extrude(rotor_h + 2.0)
    )
    body = body.cut(bore)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "tube_race":
    result = build_tube_race()
elif target_part == "roller":
    result = build_roller()
else:
    result = build_rotor()
