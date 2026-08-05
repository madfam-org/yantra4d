"""
Boot / Glove Dryer Manifold — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Splits airflow from a fan, vent, or hair-dryer into several branches that push warm
air down into wet boots and gloves. One inlet leads into a plenum that fans out to N
branch tubes; the branch ends can be plain open tubes, flattened boot-shaped outlets,
or the whole thing can carry a wall-mount plate. Dry outdoor gear overnight without a
commercial rack.

Design idiom (hollow plenum + branch tubes):
  A central plenum (a short cylinder) has one inlet socket on the bottom and N branch
  tubes fanning up-and-out around the top. Each branch is an angled cylinder rooted
  into the plenum wall (volumetric overlap), then a single interior cut hollows the
  plenum and every branch bore at once by unioning all the inner cylinders and cutting
  them from the solid. Building solid-then-hollow keeps the shell watertight.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `inlet_dia`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
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
target_part = str(  PARAM(lambda: target_part, "manifold"))  # manifold | boot_tree | wall_mount
inlet_dia   = float(PARAM(lambda: inlet_dia,   60.0))         # duct / fan inlet diameter (mm)
branches    = int(  PARAM(lambda: branches,       2))         # number of branch tubes
branch_dia  = float(PARAM(lambda: branch_dia,  38.0))         # branch tube diameter (mm)
branch_len  = float(PARAM(lambda: branch_len,  70.0))         # branch tube length (mm)
branch_ang  = float(PARAM(lambda: branch_ang,  35.0))         # branch splay angle from vertical (deg)
wall        = float(PARAM(lambda: wall,         3.0))         # shell wall thickness (mm)
inlet_depth = float(PARAM(lambda: inlet_depth, 20.0))         # inlet socket depth (mm)

# ── Clamp to sane ranges so extreme UI values still build watertight ─────────
inlet_dia = max(20.0, min(inlet_dia, 150.0))
branches = max(2, min(branches, 6))
branch_dia = max(12.0, min(branch_dia, 90.0))
branch_len = max(20.0, min(branch_len, 200.0))
branch_ang = max(0.0, min(branch_ang, 70.0))
wall = max(1.6, min(wall, 8.0))
inlet_depth = max(8.0, min(inlet_depth, 60.0))

inlet_r = inlet_dia / 2.0
inlet_bore_r = inlet_r + 0.5          # slip over the duct
branch_r = branch_dia / 2.0
branch_bore_r = max(2.0, branch_r - wall)
# Plenum sized to seat the inlet and fan the branches.
plenum_r = max(inlet_r + wall + 2.0, branch_r + wall)
plenum_h = max(18.0, branch_dia * 0.8)


# ── Branch geometry ────────────────────────────────────────────────────────────
def _branch_axis(k):
    """Direction + seat point for branch k, splayed `branch_ang` from +Z and spread
    evenly in azimuth around the plenum top."""
    az = 360.0 / branches * k
    return az, branch_ang


def _branch_solid(k, radius, length, root_bury):
    """A branch cylinder (outer if radius=branch_r, bore if radius=branch_bore_r).
    Rooted at the plenum top center, leaning `branch_ang` and rotated to azimuth az.
    `root_bury` extends the cylinder back into the plenum for a volumetric join."""
    az, ang = _branch_axis(k)
    cyl = cq.Workplane("XY").circle(radius).extrude(length + root_bury).translate((0, 0, -root_bury))
    cyl = cyl.rotate((0, 0, 0), (0, 1, 0), ang)     # lean from +Z toward +X
    cyl = cyl.rotate((0, 0, 0), (0, 0, 1), az)      # spin to azimuth
    cyl = cyl.translate((0, 0, plenum_h))           # seat at plenum top
    return cyl


def _plenum_solid():
    """The central plenum body (solid cylinder) plus a stub inlet collar below."""
    plenum = cq.Workplane("XY").circle(plenum_r).extrude(plenum_h)
    # Inlet collar hanging below z=0.
    collar = cq.Workplane("XY").circle(inlet_bore_r + wall).extrude(-inlet_depth)
    # Dome the top a touch so branches blend (a short cap).
    body = plenum.union(collar)
    return body


def build_manifold(flatten=False):
    """Inlet + plenum + N branches, hollowed by one combined interior cut. If
    `flatten`, the branch tips are squished to an oval boot-shaped outlet.

    The interior is ONE connected void: an open plenum chamber (no solid cap under
    the branches), the inlet bore below it, and every branch bore. The branch bores
    only bury a short `bore_bury` into the plenum so their angled cuts don't sever
    the plenum walls into separate solids — the shared plenum chamber is what joins
    all bores, giving a single watertight solid."""
    body = _plenum_solid()

    # Outer branch tubes weld deep into the plenum for a volumetric join.
    for k in range(branches):
        body = body.union(_branch_solid(k, branch_r, branch_len, plenum_r + 2.0))

    # ── One connected interior void ──
    # Plenum chamber: a cylinder that stops `cap` below the plenum top, leaving a
    # SOLID cap disc there. Each branch welds onto that cap (outer radius > bore
    # radius, so a solid shoulder joins branch→cap) and its bore drills DOWN through
    # the cap into the chamber. The cap is what keeps branches fused to the plenum —
    # without it, a wide chamber would undercut the branch roots and float them off.
    cap = max(1.6, wall)
    void = cq.Workplane("XY").circle(plenum_r - wall).extrude(plenum_h - cap)
    # Inlet bore through the collar into the chamber.
    void = void.union(
        cq.Workplane("XY").circle(inlet_bore_r).extrude(inlet_depth + plenum_h - cap).translate((0, 0, -inlet_depth - 1.0))
    )
    # Branch bores: over-run the tips (open ends) and bury enough to pierce the cap
    # into the chamber, but not so deep as to carve the plenum walls apart.
    bore_bury = cap + max(3.0, wall) + 1.0
    for k in range(branches):
        void = void.union(_branch_solid(k, branch_bore_r, branch_len + 3.0, bore_bury))
    body = body.cut(void)

    if flatten:
        body = _flatten_tips(body)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def _flatten_tips(body):
    """Squeeze each branch tip toward an oval boot outlet by shaving two flats near
    the open end. Non-fatal per branch."""
    for k in range(branches):
        az, ang = _branch_axis(k)
        # Build two shaving blocks on either side of the branch at its tip.
        for sign in (+1.0, -1.0):
            blk = (
                cq.Workplane("XY")
                .box(branch_dia * 1.4, branch_dia * 0.5, branch_len * 0.6, centered=(True, True, False))
                .translate((0, sign * (branch_r + branch_dia * 0.20), branch_len * 0.55))
            )
            blk = blk.rotate((0, 0, 0), (0, 1, 0), ang).rotate((0, 0, 0), (0, 0, 1), az).translate((0, 0, plenum_h))
            try:
                body = body.cut(blk)
            except Exception:
                pass
    return body


def build_wall_mount():
    """The manifold plus a flat back plate with screw holes so it hangs on a wall
    with branches pointing out. The plate is built on +Y (so the plenum is between
    the wall and the branches) and OVERLAPS the plenum by `ov` so the union is a
    single watertight solid, plus a connecting boss guarantees fusion even when the
    branches splay clear of the plate."""
    body = build_manifold(flatten=False)
    plate_w = max(plenum_r * 2.0 + 20.0, branch_len)
    plate_h = plenum_h + branch_len * math.cos(math.radians(branch_ang)) * 0.6 + 20.0
    plate_t = max(3.0, wall)
    ov = 2.0  # how far the plate bites into the plenum

    # XZ workplane extrudes toward -Y (into the page); build the plate on the -Y side
    # of the plenum, its front face pushed `ov` INTO the plenum body.
    plate_front_y = plenum_r - ov          # inside the plenum
    plate = (
        cq.Workplane("XZ")
        .workplane(offset=plate_front_y)
        .center(0.0, plate_h / 2.0 - 5.0)
        .rect(plate_w, plate_h)
        .extrude(plate_t + ov)             # extrude -Y by (plate_t+ov): back face at -(plate_t)
    )
    # A connecting boss (a solid block bridging plenum center to the plate) so the
    # weld is volumetric regardless of branch geometry.
    boss = (
        cq.Workplane("XZ")
        .workplane(offset=plate_front_y)
        .center(0.0, plenum_h / 2.0)
        .rect(plenum_r * 1.2, plenum_h)
        .extrude(plate_t + ov + plenum_r)
    )
    body = body.union(plate).union(boss)

    # Screw holes through the plate ONLY. An XZ workplane extrudes toward -Y, so put
    # the cutter's near face just in FRONT of the plate (offset = plate_front_y - 1)
    # and extrude back through the whole plate thickness. Holes sit in the plate's
    # outer margin (out past the plenum footprint) so the cut never reaches the
    # chamber and cannot sever the body.
    hx_off = plenum_r + (plate_w / 2.0 - plenum_r) * 0.6   # out past the plenum edge
    for sx in (-1.0, 1.0):
        for sz in (0.18, 0.82):
            hole = (
                cq.Workplane("XZ")
                .workplane(offset=plate_front_y - 1.0)    # just in front of the plate
                .center(sx * hx_off, plate_h * sz - 5.0)
                .circle(2.6)
                .extrude(plate_t + ov + 2.0)              # back through the plate
            )
            try:
                body = body.cut(hole)
            except Exception:
                pass
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "boot_tree":
    result = build_manifold(flatten=True)
elif target_part == "wall_mount":
    result = build_wall_mount()
else:
    result = build_manifold(flatten=False)
