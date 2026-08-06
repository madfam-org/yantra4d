"""
Geodesic / Strut Hub Connector — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A central hub that joins several struts (dowels, tubes, or pipes) at defined
angles — the vertex node for domes, shelters, tensegrity frames, trellises, and
geodesic structures. Each strut plugs into a cylindrical socket carried on an arm
that radiates from a solid central body. Optional cross-holes let a pin or screw
lock every strut into its socket.

Three modes (dispatched via `target_part`):
  * "flat_hub"      — all struts lie in one plane at equal angular spacing
                      (radial_flat); a planar node / hub-and-spoke connector.
  * "dome_hub"      — the strut arms tilt UP out of the plane by `cone_angle`
                      (cone); the classic geodesic-dome vertex.
  * "ground_anchor" — struts point up from a flat, stake-able base plate that
                      pins the structure to the ground.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `strut_dia`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq
import math


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


# ── Preset dome-vertex geometries ────────────────────────────────────────────
# A 2V icosahedral geodesic dome has vertices where either 5 or 6 struts meet.
# "custom_5v" ships a representative 5-way dome vertex whose arms sit on a shallow
# cone (the average incidence at a 2V pentagon vertex ≈ 12° above the tangent
# plane). It is an approachable, buildable node — not a survey-grade calculation.
DOME_5V = {"struts": 5, "cone_angle": 12.0}


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "flat_hub"))  # flat_hub|dome_hub|ground_anchor
if target_part not in ("flat_hub", "dome_hub", "ground_anchor"):
    target_part = "flat_hub"

hub_style = str(PARAM(lambda: hub_style, "radial_flat"))    # radial_flat|cone|custom_5v
if hub_style not in ("radial_flat", "cone", "custom_5v"):
    hub_style = "radial_flat"

strut_dia = float(PARAM(lambda: strut_dia, 12.0))           # strut / dowel diameter (socket bore)
struts = int(PARAM(lambda: struts, 5))                      # number of struts to join
socket_depth = float(PARAM(lambda: socket_depth, 22.0))     # how deep a strut seats
socket_wall = float(PARAM(lambda: socket_wall, 3.0))        # wall around the socket bore
clearance = float(PARAM(lambda: clearance, 0.4))            # bore = strut_dia + clearance (print fit)
cone_angle = float(PARAM(lambda: cone_angle, 25.0))         # arm rise above the plane (cone / dome)
pin_holes = bool(PARAM(lambda: pin_holes, True))            # cross-holes to pin/screw each strut
pin_dia = float(PARAM(lambda: pin_dia, 3.5))               # pin / screw hole diameter
anchor_dia = float(PARAM(lambda: anchor_dia, 70.0))         # ground_anchor base plate diameter
anchor_thick = float(PARAM(lambda: anchor_thick, 5.0))      # ground_anchor base plate thickness

# ── Resolve style / mode interactions ────────────────────────────────────────
# The custom_5v preset fixes strut count + cone angle to a buildable dome vertex.
if hub_style == "custom_5v":
    struts = DOME_5V["struts"]
    cone_angle = DOME_5V["cone_angle"]

# Clamp to sane, watertight ranges.
struts = max(2, min(struts, 12))
strut_dia = max(3.0, strut_dia)
socket_wall = max(1.5, socket_wall)
socket_depth = max(6.0, socket_depth)
clearance = max(0.0, min(clearance, 1.5))
pin_dia = max(1.0, min(pin_dia, strut_dia * 0.8))

bore_dia = strut_dia + clearance
socket_outer_dia = bore_dia + 2.0 * socket_wall

# Effective rise of the arms above the tangent plane.
if target_part == "ground_anchor":
    # Struts point up out of the base; steep by default so the frame stands.
    rise_deg = max(45.0, cone_angle) if hub_style != "radial_flat" else 90.0
    if hub_style == "radial_flat":
        rise_deg = 90.0
elif target_part == "dome_hub" or hub_style in ("cone", "custom_5v"):
    rise_deg = max(0.0, min(cone_angle, 80.0))
else:  # flat_hub + radial_flat
    rise_deg = 0.0

# Central body sized so every arm root is fully embedded (watertight union).
# A short cylindrical core (flat faces) unions with the cylindrical arms far more
# reliably than a sphere would — no near-tangent sliver faces. The radius must be
# large enough that neighbouring arm roots sit side-by-side on the rim instead of
# deeply crossing each other inside a too-small core (which corrupts the boolean).
# Required rim radius so N circles of the arm radius fit around the circumference:
_arm_r = socket_outer_dia / 2.0
if struts >= 3:
    # chord spacing: 2*R*sin(pi/N) >= arm_dia  →  R >= arm_r / sin(pi/N)
    _min_ring_r = _arm_r / max(0.15, math.sin(math.pi / struts))
else:
    _min_ring_r = _arm_r * 1.6
body_r = max(socket_outer_dia * 0.85 + 6.0, _min_ring_r + 2.0)
body_dia = 2.0 * body_r
body_h = max(socket_outer_dia, body_dia * 0.6)


# ── Helpers ──────────────────────────────────────────────────────────────────
def central_body():
    """A short cylindrical core all arms fuse into, centred on the origin."""
    return cq.Workplane("XY").cylinder(body_h, body_r)


def one_arm(rise_deg):
    """Build a single strut arm pointing along +X, tilted UP by `rise_deg`, as a
    solid rod with a blind socket bore and optional pin cross-hole.

    The rod's inner end is embedded a fixed depth past the core rim so it always
    overlaps the central core by a solid margin (watertight union) without every
    root piling up at the exact centre."""
    embed = min(body_r * 0.9, _arm_r + 4.0)     # how far the root sits inside the rim
    overlap = body_r + embed                    # base offset so the root reaches inside
    arm_len = socket_depth + socket_wall + overlap
    # Solid outer rod along +Z first (easy to bore), then rotate to +X.
    rod = (
        cq.Workplane("XY")
        .circle(socket_outer_dia / 2.0)
        .extrude(arm_len)
    )
    # Blind socket bored from the FAR (outer) end, leaving a stop at the base.
    bore = (
        cq.Workplane("XY")
        .workplane(offset=arm_len)
        .circle(bore_dia / 2.0)
        .extrude(-socket_depth)
    )
    rod = rod.cut(bore)

    # Optional pin/screw cross-hole through the socket walls + strut.
    if pin_holes:
        pin_z = arm_len - socket_depth * 0.5
        pin = (
            cq.Workplane("XZ")
            .workplane(offset=-socket_outer_dia)  # start well outside one wall
            .center(pin_z, 0)
            .circle(pin_dia / 2.0)
            .extrude(socket_outer_dia * 2.0)
        )
        rod = rod.cut(pin)

    # The rod points +Z with its base at z=0. Shift DOWN by `overlap` so the base
    # sits below the origin, then rotate to +X tilted up by rise_deg. This drives
    # the solid root deep into the core regardless of tilt.
    rod = rod.translate((0, 0, -overlap))
    rod = rod.rotate((0, 0, 0), (0, 1, 0), 90.0 - rise_deg)
    return rod


def build_hub(rise_deg, with_base=False):
    body = central_body()
    step = 360.0 / struts
    for i in range(struts):
        arm = one_arm(rise_deg)
        arm = arm.rotate((0, 0, 0), (0, 0, 1), i * step)
        body = body.union(arm)

    if with_base:
        base_top = -body_h / 2.0 + 0.5           # overlap the core slightly
        base_t = max(2.0, anchor_thick)
        base = (
            cq.Workplane("XY")
            .workplane(offset=base_top)
            .circle(anchor_dia / 2.0)
            .extrude(-base_t)
        )
        # Stake holes: a ring of holes near the base rim for tent pegs / screws.
        peg_dia = 6.0
        ring_r = anchor_dia / 2.0 - max(peg_dia, 6.0)
        if ring_r > peg_dia:
            n_pegs = max(3, min(struts, 6))
            pts = []
            for j in range(n_pegs):
                a = math.radians(j * 360.0 / n_pegs)
                pts.append((ring_r * math.cos(a), ring_r * math.sin(a)))
            pegs = (
                cq.Workplane("XY")
                .workplane(offset=base_top + 1.0)
                .pushPoints(pts)
                .circle(peg_dia / 2.0)
                .extrude(-(base_t + 2.0))
            )
            base = base.cut(pegs)
        body = body.union(base)

    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "ground_anchor":
    result = build_hub(rise_deg, with_base=True)
elif target_part == "dome_hub":
    result = build_hub(rise_deg, with_base=False)
else:  # flat_hub
    result = build_hub(rise_deg, with_base=False)
