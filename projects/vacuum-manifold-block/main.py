"""
Vacuum Manifold Block — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The middle of the soft-pneumatic chain: source → manifold → actuator. A solid
prism drilled with one plenum running its length, an inlet port at one end, and
N outlet ports on a fixed pitch along a face. Feed it from a vacuum ejector or
a small pump and it drives an array of `suction-cup-bellows`; feed it pressure
and it drives an array of `bellows-actuator` or `pneu-net-finger`.

Every port is the shared barb series from `pneumatic-barb-port`, so a manifold
generated at one `tube_id` mates every cartridge in the family generated at the
same `tube_id`. Port pitch is published as a CDG grid interface, so an array of
cups can be laid out against it without measuring.

Modes:
  - inline_manifold : N outlets along one face, inlet on the end — the common bar.
  - dual_manifold   : outlets on BOTH long faces (2N total), for a double row.
  - blank_plug      : a barb-less threaded/press plug to blank an unused outlet.

Watertight strategy: pure boolean drilling of a prism. The plenum is ONE cut
that stops short of both end walls; every port bore is a cut that intersects
the plenum; barb stems are unioned onto the prism BEFORE their bores are cut,
so no ring is ever left floating. Port count is derived from length and pitch
and floored at 1, and every bore radius is clamped against the wall so a bore
can never break out of the block at any parameter extreme.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as BARE globals.
  - Read params via PARAM(lambda: <name>, <default>). No globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.

LOW-PRESSURE / vacuum service only. Print with generous perimeters; a printed
manifold leaks at the seams if the walls are thin.
"""

import math

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
target_part = str(PARAM(lambda: target_part, "inline_manifold"))
# "inline_manifold" | "dual_manifold" | "blank_plug"

block_len  = float(PARAM(lambda: block_len,  90.0))  # block length (X)
block_w    = float(PARAM(lambda: block_w,    18.0))  # block width (Y)
block_h    = float(PARAM(lambda: block_h,    16.0))  # block height (Z)
port_pitch = float(PARAM(lambda: port_pitch, 20.0))  # outlet centre spacing — CDG grid
plenum_dia = float(PARAM(lambda: plenum_dia,  6.0))  # internal plenum bore
tube_id    = float(PARAM(lambda: tube_id,     4.0))  # tubing inner dia (barb series)
bore       = float(PARAM(lambda: bore,        2.6))  # port passage diameter
wall       = float(PARAM(lambda: wall,        3.0))  # minimum wall around a bore
barb_rise  = float(PARAM(lambda: barb_rise,   0.7))  # barb ridge height
mount_dia  = float(PARAM(lambda: mount_dia,   4.3))  # M4 mounting-hole clearance

# ── Clamps ───────────────────────────────────────────────────────────────────
block_len  = max(20.0, min(block_len, 300.0))
block_w    = max(8.0,  min(block_w, 80.0))
block_h    = max(8.0,  min(block_h, 80.0))
port_pitch = max(6.0,  min(port_pitch, 100.0))
plenum_dia = max(2.0,  min(plenum_dia, 40.0))
tube_id    = max(1.5,  min(tube_id, 12.0))
bore       = max(0.8,  min(bore, 10.0))
wall       = max(1.0,  min(wall, 15.0))
barb_rise  = max(0.2,  min(barb_rise, 2.0))
mount_dia  = max(1.5,  min(mount_dia, 12.0))

# ── Derived, clamped so a bore can never break out of the block ──────────────
# The plenum runs along X at the block's centre; it must leave `wall` on every
# side in both Y and Z.
PLEN_R = min(
    plenum_dia / 2.0,
    block_w / 2.0 - wall,
    block_h / 2.0 - wall,
)
PLEN_R = max(0.6, PLEN_R)

# Port bore must fit inside the plenum's cross-section AND leave a stem wall.
STEM_R = max(tube_id / 2.0, bore / 2.0 + 0.8)
BORE_R = min(bore / 2.0, STEM_R - 0.6, PLEN_R * 0.85)
BORE_R = max(0.35, BORE_R)
BARB_R = STEM_R + barb_rise
STEM_L = 9.0

# Ports along X; always at least one, always inside the end walls.
USABLE = block_len - 2.0 * (STEM_R + wall)
N_PORT = max(1, int(USABLE // port_pitch) + 1) if USABLE > 0 else 1
FIELD = (N_PORT - 1) * port_pitch
X0 = -FIELD / 2.0

# Mounting holes at the ends, drilled Z-through OUTSIDE the plenum envelope.
MNT_R = min(mount_dia / 2.0, block_w / 2.0 - 1.2)
MNT_R = max(0.5, MNT_R)
# Offset in Y so the hole clears the plenum: must be beyond PLEN_R + MNT_R.
MNT_Y = PLEN_R + MNT_R + 1.0
MNT_OK = MNT_Y + MNT_R <= block_w / 2.0 - 0.8
MNT_X = block_len / 2.0 - MNT_R - 2.0


# ── Helpers ──────────────────────────────────────────────────────────────────
def barb_z(x, y, z0, direction):
    """A barb stem standing off the block face at (x, y, z0), pointing along
    `direction` = +1 (+Y) or -1 (-Y). Ridges widen away from the block so the
    tube locks on. Returned WITHOUT its bore — the bore is cut later."""
    # Build along +Z then rotate into the Y axis.
    body = cq.Workplane("XY").circle(STEM_R).extrude(STEM_L)
    for i in range(2):
        zb = 1.2 + i * 3.4
        zb = min(zb, STEM_L - 2.4)
        ridge = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, zb))
            .circle(BARB_R)
            .workplane(offset=2.0)
            .circle(STEM_R)
            .loft(ruled=True)
        )
        body = body.union(ridge)
    # +Z → +Y is a -90° rotation about X; -Z → -Y is +90°.
    ang = -90.0 if direction > 0 else 90.0
    body = body.rotate((0, 0, 0), (1, 0, 0), ang)
    return body.translate((x, y, z0))


def barb_x(x0, y, z, direction):
    """A barb stem on an END face, pointing along +X or -X."""
    body = cq.Workplane("XY").circle(STEM_R).extrude(STEM_L)
    for i in range(2):
        zb = 1.2 + i * 3.4
        zb = min(zb, STEM_L - 2.4)
        ridge = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, zb))
            .circle(BARB_R)
            .workplane(offset=2.0)
            .circle(STEM_R)
            .loft(ruled=True)
        )
        body = body.union(ridge)
    ang = 90.0 if direction > 0 else -90.0
    body = body.rotate((0, 0, 0), (0, 1, 0), ang)
    return body.translate((x0, y, z))


def bore_y(x, z, y_from, y_to):
    """A port passage drilled along Y."""
    length = abs(y_to - y_from)
    cyl = cq.Workplane("XY").circle(BORE_R).extrude(length)
    cyl = cyl.rotate((0, 0, 0), (1, 0, 0), -90.0)  # +Z → +Y
    return cyl.translate((x, min(y_from, y_to), z))


def bore_x(y, z, x_from, length):
    cyl = cq.Workplane("XY").circle(BORE_R).extrude(length)
    cyl = cyl.rotate((0, 0, 0), (0, 1, 0), 90.0)  # +Z → +X
    return cyl.translate((x_from, y, z))


# ── Part builders ────────────────────────────────────────────────────────────
def build_manifold(dual=False):
    """Prism + plenum + inlet + N (or 2N) outlet barbs."""
    body = (
        cq.Workplane("XY")
        .box(block_len, block_w, block_h, centered=(True, True, False))
    )
    z_mid = block_h / 2.0

    # ── Union every barb stem FIRST, so no bore ever leaves a floating ring ──
    for i in range(N_PORT):
        x = X0 + i * port_pitch
        body = body.union(barb_z(x, block_w / 2.0, z_mid, +1))
        if dual:
            body = body.union(barb_z(x, -block_w / 2.0, z_mid, -1))
    # Inlet on the -X end face.
    body = body.union(barb_x(-block_len / 2.0, 0.0, z_mid, -1))

    # ── Now the cuts ────────────────────────────────────────────────────────
    # Plenum along X, stopping short of both end walls.
    plen_len = block_len - 2.0 * wall
    plen_len = max(2.0, plen_len)
    plenum = cq.Workplane("XY").circle(PLEN_R).extrude(plen_len)
    plenum = plenum.rotate((0, 0, 0), (0, 1, 0), 90.0)
    plenum = plenum.translate((-plen_len / 2.0, 0.0, z_mid))
    body = body.cut(plenum)

    # Outlet passages: from outside the barb tip into the plenum centreline.
    reach = block_w / 2.0 + STEM_L + 2.0
    for i in range(N_PORT):
        x = X0 + i * port_pitch
        body = body.cut(bore_y(x, z_mid, -0.5, reach))
        if dual:
            body = body.cut(bore_y(x, z_mid, -reach, 0.5))

    # Inlet passage from the barb tip into the plenum.
    in_len = STEM_L + wall + 3.0
    body = body.cut(bore_x(0.0, z_mid, -block_len / 2.0 - STEM_L - 1.0, in_len))

    # Mounting holes, only when they demonstrably clear the plenum.
    if MNT_OK and MNT_X > MNT_R:
        tool = None
        for sx in (-1, 1):
            for sy in (-1, 1):
                h = (
                    cq.Workplane("XY")
                    .transformed(offset=cq.Vector(sx * MNT_X, sy * MNT_Y, -1.0))
                    .circle(MNT_R)
                    .extrude(block_h + 2.0)
                )
                tool = h if tool is None else tool.union(h)
        if tool is not None:
            body = body.cut(tool)
    return body


def build_blank_plug():
    """A press-in plug to blank an unused outlet: a stepped stub with a grip
    head, sized to the same port bore the manifold drills."""
    plug_r = max(0.6, BORE_R - 0.08)      # slight interference press fit
    plug_l = max(3.0, wall + 3.0)
    head_r = plug_r + max(1.2, wall * 0.6)
    head_h = max(1.6, wall * 0.7)
    body = cq.Workplane("XY").circle(head_r).extrude(head_h)
    stub = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, head_h))
        .circle(plug_r)
        .extrude(plug_l)
    )
    body = body.union(stub)
    # Lead-in taper on the stub tip so it starts square.
    try:
        body = body.faces(">Z").edges().chamfer(min(0.5, plug_r * 0.35))
    except Exception:
        pass
    # Knurl-ish grip: shallow flats on the head, one fused cutting tool.
    tool = None
    for k in range(6):
        ang = 2.0 * math.pi * k / 6.0
        d = head_r * 0.94
        notch = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(d * math.cos(ang), d * math.sin(ang), -0.5))
            .circle(max(0.3, head_r * 0.22))
            .extrude(head_h + 1.0)
        )
        tool = notch if tool is None else tool.union(notch)
    if tool is not None:
        body = body.cut(tool)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "dual_manifold":
    result = build_manifold(dual=True)
elif target_part == "blank_plug":
    result = build_blank_plug()
else:  # "inline_manifold"
    result = build_manifold(dual=False)
