"""
Gear / Linkage Learning Kit — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A snap-together STEM kit for teaching gear ratios, torque and linkages. Every
part shares one Common Denominator Geometry: a square PEG GRID on an 8 mm pitch
with round pegs, so gears, idlers and linkage bars relocate to any grid node and
mesh correctly. Unlike a bare gear generator, this cartridge produces the three
interoperating pieces a classroom set needs:

  - gear_plate : an involute spur gear (ISO 53 / DIN 867, 20° pressure angle)
                 carrying a central round hub that drops onto a grid peg and
                 turns freely, plus a finger crank knob.
  - link_bar   : a flat linkage bar with a row of grid-pitch pivot holes — the
                 four-bar/pantograph element that couples gear axles.
  - peg_base   : a baseboard tile with an m x n array of upright pegs on the
                 grid pitch; gears and links mount and rotate on the pegs.

Interoperability figures (cited as the CDG `standard` = "internal peg grid 8mm"):
  - grid pitch          = 8.0 mm   (peg-to-peg spacing, both axes)
  - peg diameter        = 4.0 mm   (upright pin the hubs turn on)
  - hub bore clearance  ≈ 0.4 mm   (running fit → gear spins on the peg)

Watertight strategy:
  Gear body is an extrusion of the closed involute wire (single solid). The hub
  is a SOLID cylinder unioned coaxially (overlapping into the gear), then a
  through bore is cut from below all the way through — the bore vents to both
  faces so no trapped void. The crank knob is a solid post unioned on top with
  its own through grip hole. The link bar is a rounded slab with through holes.
  The peg base is a slab with SOLID peg cylinders unioned on top (overlapping),
  fillets applied to the blank slab BEFORE features. No revolve-of-cut profiles.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `target_part`).
  - Read them via PARAM(lambda: <name>, <default>); the render worker injects
    target_part = <mode.parts[0]>. Do NOT use globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq
import math


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "gear_plate"))
# "gear_plate" | "link_bar" | "peg_base"

grid_pitch = float(PARAM(lambda: grid_pitch, 8.0))    # peg-to-peg spacing (mm)
peg_dia = float(PARAM(lambda: peg_dia, 4.0))          # upright peg diameter (mm)
peg_clear = float(PARAM(lambda: peg_clear, 0.4))      # bore-over-peg running clearance (mm)

module = float(PARAM(lambda: module, 2.0))            # gear module (mm)
teeth = int(PARAM(lambda: teeth, 16))                 # number of teeth
pressure_angle = float(PARAM(lambda: pressure_angle, 20.0))  # deg
gear_thick = float(PARAM(lambda: gear_thick, 6.0))    # gear face width (mm)
hub_height = float(PARAM(lambda: hub_height, 5.0))    # hub rise above the gear face (mm)
crank = bool(PARAM(lambda: crank, True))              # add a finger-crank knob

link_holes = int(PARAM(lambda: link_holes, 4))        # pivot holes along the link bar
link_thick = float(PARAM(lambda: link_thick, 4.0))    # link bar thickness (mm)

base_cols = int(PARAM(lambda: base_cols, 4))          # peg-base columns (X)
base_rows = int(PARAM(lambda: base_rows, 4))          # peg-base rows (Y)
base_thick = float(PARAM(lambda: base_thick, 4.0))    # baseboard slab thickness (mm)
peg_len = float(PARAM(lambda: peg_len, 10.0))         # peg length above the slab (mm)

# ── Clamp inputs so extreme UI values never crash the kernel ─────────────────
grid_pitch = max(5.0, min(grid_pitch, 20.0))
peg_dia = max(2.0, min(peg_dia, grid_pitch - 1.0))
peg_clear = max(0.1, min(peg_clear, 1.0))
module = max(0.8, min(module, 4.0))
teeth = max(8, min(teeth, 60))
pressure_angle = max(14.5, min(pressure_angle, 25.0))
gear_thick = max(2.0, min(gear_thick, 16.0))
hub_height = max(2.0, min(hub_height, 20.0))
link_holes = max(2, min(link_holes, 12))
link_thick = max(2.0, min(link_thick, 10.0))
base_cols = max(2, min(base_cols, 8))
base_rows = max(2, min(base_rows, 8))
base_thick = max(2.0, min(base_thick, 10.0))
peg_len = max(4.0, min(peg_len, 30.0))

pa = math.radians(pressure_angle)
bore_r = (peg_dia + peg_clear) / 2.0   # running-fit hub bore radius


# ── Involute gear geometry (ISO 53 / DIN 867) ────────────────────────────────
def _involute_point(rb, t):
    return (rb * (math.cos(t) + t * math.sin(t)),
            rb * (math.sin(t) - t * math.cos(t)))


def _inv(angle):
    return math.tan(angle) - angle


def _roll_at_radius(rb, r):
    if r <= rb:
        return 0.0
    return math.sqrt((r / rb) ** 2 - 1.0)


def _one_tooth(rb, ro, rr, n):
    """Ordered (x, y) outline of one tooth, centred on +X."""
    half_pitch = math.pi / (2.0 * teeth)
    beta0 = half_pitch + _inv(pa)
    r_start = max(rb, rr)
    t_end = _roll_at_radius(rb, ro)
    t_start = _roll_at_radius(rb, r_start)
    right = []
    for i in range(n):
        t = t_start + (t_end - t_start) * (i / (n - 1))
        x0, y0 = _involute_point(rb, t)
        phi = math.atan2(y0, x0)
        r = rb * math.sqrt(1.0 + t * t)
        ang = phi - beta0
        right.append((r * math.cos(ang), r * math.sin(ang)))
    root_r = []
    if rr < r_start - 1e-6:
        fx, fy = right[0]
        fang = math.atan2(fy, fx)
        root_r.append((rr * math.cos(fang), rr * math.sin(fang)))
    left = [(x, -y) for (x, y) in reversed(right)]
    root_l = [(x, -y) for (x, y) in reversed(root_r)]
    pts = []
    pts.extend(root_r)
    pts.extend(right)
    pts.extend(left)
    pts.extend(root_l)
    return pts


def _gear_wire():
    rp = module * teeth / 2.0
    rb = rp * math.cos(pa)
    ro = rp + module
    rr = max(rp - 1.25 * module, 0.5 * module)
    tooth = _one_tooth(rb, ro, rr, 9)
    step = 2.0 * math.pi / teeth
    all_pts = []
    for k in range(teeth):
        a = k * step
        ca, sa = math.cos(a), math.sin(a)
        for (x, y) in tooth:
            all_pts.append((x * ca - y * sa, x * sa + y * ca))
    return all_pts


def build_gear_plate():
    """Involute spur gear with a hub bore (runs on a grid peg) + finger crank."""
    wire = _gear_wire()
    gear = cq.Workplane("XY").polyline(wire).close().extrude(gear_thick)

    # Solid hub coaxial with the gear, overlapping into the gear body.
    rp = module * teeth / 2.0
    hub_r = max(bore_r + 2.0, min(peg_dia / 2.0 + 3.0, rp - module))
    hub = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, gear_thick - 0.01))
        .circle(hub_r)
        .extrude(hub_height + 0.01)
    )
    body = gear.union(hub)
    top_z = gear_thick + hub_height

    # Optional finger crank: an off-centre solid post on top of the hub with a
    # through grip hole (vents both ends → no trapped void).
    if crank:
        knob_r = max(2.5, hub_r * 0.55)
        off = max(hub_r - knob_r - 0.5, hub_r * 0.35)
        knob = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(off, 0, top_z - 0.01))
            .circle(knob_r)
            .extrude(gear_thick + 0.01)
        )
        body = body.union(knob)
        knob_top = top_z + gear_thick
        grip = (
            cq.Workplane("XZ")
            .transformed(offset=cq.Vector(off, top_z + gear_thick / 2.0, 0))
            .circle(max(0.8, knob_r * 0.35))
            .extrude(knob_r * 3.0, both=True)
        )
        body = body.cut(grip)
        top_z = knob_top

    # Central bore all the way through from below → vents both faces.
    bore = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -1.0))
        .circle(bore_r)
        .extrude(top_z + 2.0)
    )
    body = body.cut(bore)
    return body


def build_link_bar():
    """A flat linkage bar: rounded slab with a row of grid-pitch pivot holes."""
    n = link_holes
    length = (n - 1) * grid_pitch + 2.0 * grid_pitch
    width = grid_pitch * 1.6
    slab = (
        cq.Workplane("XY")
        .box(length, width, link_thick, centered=(True, True, False))
    )
    # Fillet the blank BEFORE cutting features.
    try:
        slab = slab.edges("|Z").fillet(min(width * 0.35, grid_pitch * 0.5))
    except Exception:
        pass

    x0 = -(n - 1) * grid_pitch / 2.0
    centers = [(x0 + i * grid_pitch, 0.0) for i in range(n)]
    holes = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -1.0))
        .pushPoints(centers)
        .circle(bore_r)
        .extrude(link_thick + 2.0)
    )
    body = slab.cut(holes)
    return body


def build_peg_base():
    """A baseboard tile with an array of upright pegs on the grid pitch."""
    margin = grid_pitch
    w = (base_cols - 1) * grid_pitch + 2.0 * margin
    d = (base_rows - 1) * grid_pitch + 2.0 * margin
    slab = (
        cq.Workplane("XY")
        .box(w, d, base_thick, centered=(True, True, False))
    )
    try:
        slab = slab.edges("|Z").fillet(min(margin * 0.5, 3.0))
    except Exception:
        pass

    x0 = -(base_cols - 1) * grid_pitch / 2.0
    y0 = -(base_rows - 1) * grid_pitch / 2.0
    centers = []
    for c in range(base_cols):
        for rr in range(base_rows):
            centers.append((x0 + c * grid_pitch, y0 + rr * grid_pitch))
    # SOLID peg cylinders unioned on top, overlapping into the slab.
    pegs = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, base_thick - 0.01))
        .pushPoints(centers)
        .circle(peg_dia / 2.0)
        .extrude(peg_len + 0.01)
    )
    # Round the peg tops so parts drop on easily (chamfer top edge, keep solid).
    body = slab.union(pegs)
    try:
        body = body.faces(">Z").edges("%CIRCLE").chamfer(min(0.6, peg_dia * 0.15))
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "link_bar":
    result = build_link_bar()
elif target_part == "peg_base":
    result = build_peg_base()
else:
    result = build_gear_plate()
