"""
Hose Barb Tee — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The junction the commons' own tube series never had.

`pneumatic-barb-port` publishes a barb series sized by tube INNER diameter —
2 / 3 / 4 mm — and four more cartridges consume it: `bellows-actuator`,
`pneu-net-finger`, `suction-cup-bellows` and `vacuum-manifold-block`. Five
objects speak one tube series, and between any two of them there is a length of
silicone tube and nothing else. No tee. No elbow. No reducer. No way to plug one
cartridge's barb straight into another's port. A soft-pneumatic rig with two
actuators is therefore a rig with a hand-cut splice in it.

This is that missing fitting set, generated on exactly the same series: a stem
built here at `tube_id` = 3 grips the same tube as a port built there at
`tube_id` = 3, because both derive their stem radius from the same expression.

Modes are dispatched via `target_part`:
  * "tee"     — three ports on one hub: a run through, and a branch.
  * "elbow"   — two ports at a settable angle, 30 to 150 degrees.
  * "reducer" — a straight coupler between two different tube sizes.

Every mode's first port takes a selectable FORM, which is the point of the
cartridge as much as the junction is:
  * "barb"    — a barbed stem, for tube.
  * "socket"  — a plain socket that receives ANOTHER cartridge's barb stem
                directly, with no tube between them.
  * "push_in" — a parallel rigid stem for a commercial one-touch collet fitting.

The socket form is deliberate. All five members of the series publish their barb
as a `profile`, and a profile does not mate a profile — so the series is
published but not self-mating. A socket is what consumes it.

Watertightness strategy:
  * Every stem STRADDLES the hub: it starts inside the hub body, never at its
    surface, so each fuse is volumetric at every angle and every tube size.
  * The hub radius is DERIVED from the largest port it must carry plus a wall,
    so a small hub can never be swallowed by a large port.
  * Barb ridges are lofted collars clamped INSIDE their stem's own span, never
    floating rings; the ridge count is reduced until they fit, rather than being
    drawn past the end of the stem.
  * All bores are cut LAST and every one of them opens to atmosphere, so no
    internal void is ever sealed.
  * No spheres anywhere. A sphere's poles are degenerate points where every
    meridian meets, and OCC reports the solid valid while the mesh comes back
    non-watertight and split in two.
  * No fillet on any edge a bore has touched.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as BARE globals.
  - Read them via PARAM(lambda: <name>, <default>). No globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.

Printed barbs are for LOW-PRESSURE work — soft actuators, vacuum, gravity feed.
See the README.
"""

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present and non-None, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "tee"))
port_a_form = str(PARAM(lambda: port_a_form, "barb"))

tube_id = float(PARAM(lambda: tube_id, 3.0))
tube_id_b = float(PARAM(lambda: tube_id_b, 2.0))
barb_count = float(PARAM(lambda: barb_count, 3.0))
barb_pitch = float(PARAM(lambda: barb_pitch, 3.0))
barb_rise = float(PARAM(lambda: barb_rise, 0.7))
bore = float(PARAM(lambda: bore, 1.6))
wall = float(PARAM(lambda: wall, 1.6))
elbow_angle = float(PARAM(lambda: elbow_angle, 90.0))
push_od = float(PARAM(lambda: push_od, 6.0))
clearance = float(PARAM(lambda: clearance, 0.25))

# Input clamps, matching the manifest slider bounds exactly. `tube_id` shares
# the same 1.5-10 range as `pneumatic-barb-port`, deliberately: a series is only
# a series if both ends of it accept the same numbers.
tube_id = max(1.5, min(tube_id, 10.0))
tube_id_b = max(1.5, min(tube_id_b, 10.0))
barb_count = int(max(1, min(round(barb_count), 6)))
barb_pitch = max(1.6, min(barb_pitch, 8.0))
barb_rise = max(0.2, min(barb_rise, 2.0))
bore = max(0.8, min(bore, 8.0))
wall = max(0.8, min(wall, 4.0))
elbow_angle = max(30.0, min(elbow_angle, 150.0))
push_od = max(3.0, min(push_od, 10.0))
clearance = max(0.1, min(clearance, 0.6))


# ── The shared barb series ───────────────────────────────────────────────────
# These four expressions ARE the interface. They are copied from
# `pneumatic-barb-port` unchanged, so a stem generated here and a port generated
# there at the same `tube_id` grip the same tube. Changing one of them without
# changing the other would fork the series while still calling it one.
def stem_r(tid):
    """Stem outer radius: the tube ID, with a floor that keeps the bore walled."""
    return max(tid / 2.0, bore / 2.0 + wall)


def barb_r(tid):
    return stem_r(tid) + barb_rise


def bore_r(tid):
    """Passage radius, never eating more than 0.6 mm per side of the stem."""
    return max(0.35, min(bore / 2.0, stem_r(tid) - 0.6))


def ridge_h():
    return min(barb_pitch * 0.75, barb_rise * 3.0 + 0.8)


def stem_len(tid):
    """Stem length that COVERS its ridges, derived from them rather than guessed."""
    return barb_pitch * (barb_count + 0.6) + 1.5


# ── Derived, clamped against FINAL values ────────────────────────────────────
PORT_TIDS = [tube_id, tube_id, tube_id] if target_part != "reducer" else [tube_id, tube_id_b]

SOCKET_R = barb_r(tube_id) + clearance          # receives another cartridge's barb
PUSH_R = push_od / 2.0

# The hub must contain the largest thing bolted to it, plus a real wall. Derived
# from the ports, so a small tube with a large socket cannot leave a hub thinner
# than its own port wall.
_port_max = max([barb_r(t) for t in PORT_TIDS]
                + ([SOCKET_R + wall] if port_a_form == "socket" else [])
                + ([PUSH_R] if port_a_form == "push_in" else []))
HUB_R = _port_max + max(0.8, wall * 0.6)
HUB_HALF = HUB_R * 0.95                          # half-length of the hub barrel

STEM_OVERLAP = HUB_R * 0.8                       # how far a stem reaches INTO the hub


# ── Primitives ───────────────────────────────────────────────────────────────
def barbed_stem(tid, length):
    """A stem along +Z from z=0, with `barb_count` tapered ridges unioned on.

    Each ridge is a loft from the full barb radius DOWN to the stem radius, so
    the cone points back toward the hub: the tube slides on and locks. Every
    ridge is clamped inside the stem's own span; a ridge drawn past the end
    would be a floating collar, and a floating collar is a second body that no
    watertightness check reports."""
    body = cq.Workplane("XY").circle(stem_r(tid)).extrude(length)
    rh = ridge_h()
    for i in range(barb_count):
        zb = length - (1.0 + i * barb_pitch) - rh
        zb = max(0.2, min(zb, length - rh - 0.2))
        if zb < 0.2 or zb + rh > length - 0.1:
            continue
        ridge = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, zb))
            .circle(barb_r(tid))
            .workplane(offset=rh)
            .circle(stem_r(tid))
            .loft(ruled=True)
        )
        body = body.union(ridge)
    return body


def socket_port(length):
    """A plain socket that receives another cartridge's barb stem.

    Built as a plain barrel here; the receiving bore is cut with the passage,
    last, so no closed cavity ever exists at any point in the build."""
    return cq.Workplane("XY").circle(SOCKET_R + wall).extrude(length)


def push_stem(length):
    """A parallel rigid stem for a commercial push-in collet fitting.

    The collet grips a plain cylinder on its OUTSIDE diameter, so this port is a
    smooth barrel — a barbed stem would shred the collet's gripping ring."""
    return cq.Workplane("XY").circle(PUSH_R).extrude(length)


# How deep a receiving socket may be counterbored before it starts eating the
# hub. A socket bore run to full depth like a passage severs whatever port is
# opposite it whenever that port's stem is NARROWER than the socket — the far
# half of the opposite stem is simply cut off, and both halves stay perfectly
# watertight, so nothing but a body count reports it.
SOCK_STOP_Z = -max(0.0, min(HUB_HALF - 0.8, HUB_HALF - wall))


def port_solid(form, tid):
    """(solid along +Z from z = -STEM_OVERLAP, passage radius, total length,
    counterbore radius or None)."""
    if form == "socket":
        length = stem_len(tid) * 0.9 + wall
        body = socket_port(length + STEM_OVERLAP)
        # The through passage stays the small bore; the socket is a bounded
        # counterbore over it.
        return (body.translate((0, 0, -STEM_OVERLAP)), bore_r(tid), length,
                SOCKET_R)
    if form == "push_in":
        length = max(10.0, stem_len(tid) * 0.8)
        body = push_stem(length + STEM_OVERLAP)
        pr = max(0.35, min(bore / 2.0, PUSH_R - 0.8))
    else:
        length = stem_len(tid)
        body = barbed_stem(tid, length + STEM_OVERLAP)
        pr = bore_r(tid)
    return body.translate((0, 0, -STEM_OVERLAP)), pr, length, None


def oriented(solid, axis, angle):
    """Rotate a +Z-aligned solid onto an arbitrary direction."""
    if angle == 0.0:
        return solid
    return solid.rotate((0, 0, 0), axis, angle)


def passage(pr, length, axis, angle):
    """A bore along the port axis, running from inside the hub out past the end.

    Cut LAST, and always open at its far end, so it can never seal a void."""
    tool = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -HUB_R - 1.0))
        .circle(pr)
        .extrude(length + HUB_R + 2.0)
    )
    return oriented(tool, axis, angle)


def counterbore(cr, length, axis, angle):
    """A BOUNDED socket bore: from the port's far end inward, stopping short of
    the far side of the hub so the opposite port is never severed."""
    z0 = SOCK_STOP_Z
    tool = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z0))
        .circle(cr)
        .extrude((length + 1.0) - z0)
    )
    return oriented(tool, axis, angle)


def hub():
    """A short barrel at the origin that every port grows out of.

    A barrel, not a ball: a sphere's poles are degenerate points where every
    meridian meets, and the tessellator splits the result in two while OCC
    reports a single valid solid."""
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -HUB_HALF))
        .circle(HUB_R)
        .extrude(2.0 * HUB_HALF)
    )


# ── Assembly ─────────────────────────────────────────────────────────────────
def assemble(ports):
    """ports: list of (form, tube_id, rotation_axis, rotation_angle).

    Unions every port onto the hub first, THEN cuts every passage. Cutting as it
    goes would leave a moment where an open pipe end is sealed by the next
    union, and a sealed void meshes as a second body however valid the kernel
    says the solid is."""
    body = hub()
    cuts = []
    for form, tid, axis, angle in ports:
        solid, pr, length, cr = port_solid(form, tid)
        body = body.union(oriented(solid, axis, angle))
        cuts.append((pr, length, axis, angle, cr))
    for pr, length, axis, angle, cr in cuts:
        if cr is not None:
            body = body.cut(counterbore(cr, length, axis, angle))
        body = body.cut(passage(pr, length, axis, angle))
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Part builders ────────────────────────────────────────────────────────────
def build_tee():
    """Run through on X, branch on +Z. Port A is the branch."""
    return assemble([
        (port_a_form, tube_id, (0, 1, 0), 0.0),       # +Z branch
        ("barb", tube_id, (0, 1, 0), 90.0),           # +X
        ("barb", tube_id, (0, 1, 0), -90.0),          # -X
    ])


def build_elbow():
    """Two ports in the XZ plane, separated by `elbow_angle`."""
    return assemble([
        (port_a_form, tube_id, (0, 1, 0), 0.0),
        ("barb", tube_id, (0, 1, 0), 180.0 - elbow_angle),
    ])


def build_reducer():
    """A straight coupler between two different tube sizes."""
    return assemble([
        (port_a_form, tube_id, (0, 1, 0), 0.0),
        ("barb", tube_id_b, (0, 1, 0), 180.0),
    ])


# ── Dispatch ─────────────────────────────────────────────────────────────────
_dispatch = {
    "tee": build_tee,
    "elbow": build_elbow,
    "reducer": build_reducer,
}

result = _dispatch.get(target_part, build_tee)()
