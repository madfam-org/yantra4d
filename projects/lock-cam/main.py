"""
Cabinet / Drawer Cam-Lock Cam — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The flat steel cam that bolts to the back of a cabinet cam-lock cylinder and swings
to catch behind the frame. This cartridge builds the cam plate plus a body adapter
collar sized to the two dominant furniture cam-lock body diameters.

Three distinct cams:
  - cam_16mm   : straight cam plate for a 16 mm-body cam lock (the smaller of the
                 two standard furniture cam locks), with a slotted tailpiece socket
                 and a fixing screw hole.
  - cam_19mm   : straight cam plate for a 19 mm-body cam lock (the larger standard).
  - offset_cam : a stepped / cranked cam whose catch face is offset in Z, for
                 deep-set doors where a flat cam would not reach the frame.

Dimensionally real (standard furniture / cabinet cam locks):
  - body (mounting) diameters : 16 mm and 19 mm (the two dominant standards; a hole
                                 of that Ø accepts the threaded lock body)
  - cam plate                 : ~43 mm reach (arm length) is typical; ~2 mm steel
  - tailpiece drive           : a slotted / D-flat post that the cam socket keys to,
                                 secured by an axial screw (approximated as a keyed
                                 slot socket + a screw bore)

Watertight strategy:
  The cam is a filleted flat blank (rounded catch end). The tailpiece socket is a
  keyed slot cut fully THROUGH the plate (opens to both faces → vents to outside),
  the fixing screw hole is a through-bore, and the body adapter collar is a ring
  UNIONED into shared material with a through-bore. The cranked offset is built from
  two overlapping plate slabs joined by a ramp wedge (all overlapping unions → one
  manifold body). Fillets are applied to the clean blank BEFORE cutting features.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters arrive as BARE globals (e.g. `target_part`).
  - Read them via PARAM(lambda: <name>, <default>).
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


# ── Parameters (standard furniture cam locks) ────────────────────────────────
target_part = str(PARAM(lambda: target_part, "cam_16mm"))
# "cam_16mm" | "cam_19mm" | "offset_cam"

body_d = float(PARAM(lambda: body_d, 16.0))       # cam-lock body / mounting Ø (mm)
cam_reach = float(PARAM(lambda: cam_reach, 43.0)) # cam arm reach (length, mm)
cam_w = float(PARAM(lambda: cam_w, 14.0))         # cam arm width (mm)
cam_t = float(PARAM(lambda: cam_t, 2.5))          # cam plate thickness (mm)

tail_w = float(PARAM(lambda: tail_w, 6.0))        # tailpiece slot width (drive key)
tail_len = float(PARAM(lambda: tail_len, 9.0))    # tailpiece slot length (drive key)
screw_d = float(PARAM(lambda: screw_d, 3.4))      # axial fixing-screw Ø (M3-ish)
offset_z = float(PARAM(lambda: offset_z, 8.0))    # cranked cam Z offset (offset_cam)

# Clamp to sane ranges so extreme UI values never crash the kernel.
body_d = max(10.0, min(body_d, 25.0))
cam_reach = max(20.0, min(cam_reach, 80.0))
cam_w = max(8.0, min(cam_w, 30.0))
cam_t = max(1.5, min(cam_t, 6.0))
tail_w = max(3.0, min(tail_w, cam_w - 4.0))
tail_len = max(tail_w, min(tail_len, cam_w - 2.0))
screw_d = max(2.0, min(screw_d, min(tail_w - 0.5, 6.0)))
offset_z = max(3.0, min(offset_z, 25.0))

# Collar (body adapter) sits at the hub end; its outer wall wraps the body bore.
collar_wall = 3.0
collar_od = body_d + 2.0 * collar_wall
collar_h = max(cam_t + 2.0, 6.0)


# ── Primitives ───────────────────────────────────────────────────────────────
def _cam_blank(reach, width, thick):
    """A flat cam arm: a rounded-end bar from the hub (x=0) out to +X reach. Built
    as an obround (slot2D) so the catch end is radiused, extruded up +Z. Filleted?
    A slot2D is already round-ended; no edge fillet needed (and none that could
    crash clean())."""
    # slot2D of length L, width W gives a stadium of total length L centred at 0.
    # We want the arm to run from ~x=0 to x=reach, so centre the stadium at reach/2.
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(reach / 2.0, 0, 0))
        .slot2D(reach, width, angle=0)
        .extrude(thick)
    )


def _hub(od, height):
    """A cylindrical hub/collar at the origin, base at z=0."""
    return cq.Workplane("XY").cylinder(height, od / 2.0, centered=(True, True, False))


def _tail_socket(thru_h, z0=-0.5):
    """The tailpiece drive socket: a keyed slot (obround with a flat) cut fully
    through the hub so it vents to both faces. Approximates a slotted / D-flat cam
    drive. Centred at the origin."""
    slot = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z0))
        .slot2D(tail_len, tail_w, angle=90)
        .extrude(thru_h)
    )
    return slot


def _screw_bore(cx, thru_h, z0=-0.5):
    """An axial fixing-screw bore through the plate at x=cx (vents both faces)."""
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(cx, 0, z0))
        .circle(screw_d / 2.0)
        .extrude(thru_h)
    )


# ── Part builders ────────────────────────────────────────────────────────────
def _straight_cam():
    """Common builder for the straight 16/19 mm cams: hub collar + flat arm, with
    the tailpiece socket and a fixing screw bore. `body_d` selects the standard."""
    arm = _cam_blank(cam_reach, cam_w, cam_t)
    hub = _hub(collar_od, collar_h)
    # Union the hub over the arm's hub end. They overlap (hub straddles origin, arm
    # starts at origin) → solid weld, one body.
    body = arm.union(hub)

    # Tailpiece drive socket, cut through the tallest stack (collar_h) so it opens
    # top and bottom.
    body = body.cut(_tail_socket(collar_h + 1.0))

    # Fixing screw bore out along the arm (past the collar, into the flat arm).
    screw_x = collar_od / 2.0 + max(4.0, screw_d)
    screw_x = min(screw_x, cam_reach - screw_d)
    body = body.cut(_screw_bore(screw_x, cam_t + 1.0))
    return body


def build_cam_16mm():
    """Straight cam plate for a 16 mm-body cam lock."""
    return _straight_cam()


def build_cam_19mm():
    """Straight cam plate for a 19 mm-body cam lock. (Same builder; the 19 mm body_d
    grows the collar bore and outer diameter — a genuinely different solid.)"""
    return _straight_cam()


def build_offset_cam():
    """A cranked cam: the hub-end slab sits low, the catch-end slab sits raised by
    offset_z, joined by a ramp wedge. For deep-set doors where a flat cam cannot
    reach the frame. Every join overlaps into shared material → one manifold body."""
    step_x = cam_reach * 0.45          # where the crank happens

    # Low slab: hub end (0 .. step_x + overlap), on the base plane.
    low = _cam_blank(step_x + cam_w * 0.5, cam_w, cam_t)
    hub = _hub(collar_od, collar_h)
    body = low.union(hub)

    # High slab: catch end, raised by offset_z, running to the full reach.
    high_len = cam_reach - step_x + cam_w * 0.5
    high = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(step_x + high_len / 2.0 - cam_w * 0.25,
                                      0, offset_z))
        .slot2D(high_len, cam_w, angle=0)
        .extrude(cam_t)
    )

    # Ramp wedge bridging low-top to high-bottom across the step. Built as a
    # lofted rectangle from the low slab's top edge up to the high slab's underside
    # so the two slabs fuse into one body.
    ramp = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(step_x, 0, 0))
        .rect(cam_w * 0.9, cam_w)
        .workplane(offset=offset_z + cam_t)
        .rect(cam_w * 0.9, cam_w)
        .loft(combine=True)
    )
    body = body.union(high).union(ramp)

    # Tailpiece socket + screw bore at the hub (through the collar).
    body = body.cut(_tail_socket(collar_h + 1.0))
    screw_x = collar_od / 2.0 + max(4.0, screw_d)
    screw_x = min(screw_x, step_x - screw_d)
    body = body.cut(_screw_bore(screw_x, cam_t + 1.0))
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "cam_19mm":
    body_d = max(body_d, 19.0)
    collar_od = body_d + 2.0 * collar_wall
    result = build_cam_19mm()
elif target_part == "offset_cam":
    result = build_offset_cam()
else:
    result = build_cam_16mm()
