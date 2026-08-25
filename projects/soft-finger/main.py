"""
Soft Pneumatic Finger — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A single-body, print-in-place-ready pneumatic bending finger for soft robotics.
The finger is a solid ribbed beam: an accordion of external bellows ribs on the
top (extension) side and a flat strain-limiting base on the bottom. A single
internal air chamber runs the length of the finger and OPENS TO THE PROXIMAL
(base) FACE, where it meets a barbed air port sized for 4 mm ID / 6 mm OD
pneumatic tubing. Because the chamber vents to an exterior face there is NO
trapped sealed void — the whole mesh is watertight and body_count == 1.

Actuation note: printed rigid, this is a geometry master / mold pattern. For a
working actuator, cast the ribbed body in silicone from this master, or print the
walls in TPU — a fully rigid print will not inflate. See the README.

Modes:
  - bellows_finger : the full ribbed bending finger with base air port.
  - finger_tip     : a solid rounded grip cap that press-fits the finger's distal
                     end (a separate wear part / fingertip pad master).
  - base_port      : just the proximal mounting flange with the barbed 4/6 mm port
                     and screw ears — bond finger + base for a modular hand.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `target_part`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use
    globals()/eval/getattr — they are not in the sandbox's allowed builtins.
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
target_part = str(PARAM(lambda: target_part, "bellows_finger"))
# "bellows_finger" | "finger_tip" | "base_port"

finger_len = float(PARAM(lambda: finger_len, 80.0))   # overall finger length (Y)
finger_w = float(PARAM(lambda: finger_w, 20.0))       # finger width (X)
body_h = float(PARAM(lambda: body_h, 14.0))           # finger body height incl. ribs (Z)
n_ribs = int(PARAM(lambda: n_ribs, 8))                # number of bellows ribs
wall = float(PARAM(lambda: wall, 2.0))                # chamber wall thickness
chamber_w = float(PARAM(lambda: chamber_w, 12.0))     # internal air chamber width (X)
barb_od = float(PARAM(lambda: barb_od, 6.0))          # air barb outer diameter (6 mm OD tube)
barb_id = float(PARAM(lambda: barb_id, 4.0))          # air barb bore (4 mm ID tube)

# ── Clamp to sane ranges so extreme UI values never crash the kernel ──────────
finger_len = max(40.0, min(finger_len, 140.0))
finger_w = max(12.0, min(finger_w, 34.0))
body_h = max(8.0, min(body_h, 22.0))
n_ribs = max(3, min(n_ribs, 16))
wall = max(1.2, min(wall, 4.0))
chamber_w = max(4.0, min(chamber_w, finger_w - 4.0 * wall))
barb_od = max(4.0, min(barb_od, 10.0))
barb_id = max(2.0, min(barb_id, barb_od - 1.2))

base_h = 5.0            # strain-limiting base slab height (bottom, no ribs)
base_len = 14.0        # proximal solid mounting block length (Y)
ear_screw_d = 3.4      # M3 clearance for base mounting ears


# ── Helpers ──────────────────────────────────────────────────────────────────
def _base_slab():
    """The flat strain-limiting base slab under the whole finger (Y: 0..len)."""
    return (
        cq.Workplane("XY")
        .box(finger_w, finger_len, base_h, centered=(True, False, False))
    )


def _bellows_body():
    """The ribbed extension body: a run of rib blocks (full height) separated by
    thin webs (base_h + a little), unioned onto the base slab. Ribs raise the top
    surface so the extension side stretches while the base stays flat."""
    body = _base_slab()
    # Region available for ribs: leave a solid proximal block for the port.
    rib_start = base_len
    rib_zone = finger_len - rib_start - 6.0
    pitch = rib_zone / n_ribs
    rib_th = pitch * 0.6
    web_h = base_h + 1.5
    for i in range(n_ribs):
        y0 = rib_start + i * pitch
        # full-height rib block
        rib = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, y0 + rib_th / 2.0, 0))
            .box(finger_w, rib_th, body_h, centered=(True, True, False))
        )
        body = body.union(rib)
    # thin continuous web spine connecting rib tops so it prints as one wall
    spine = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, rib_start + rib_zone / 2.0, 0))
        .box(finger_w, rib_zone, web_h, centered=(True, True, False))
    )
    body = body.union(spine)
    # proximal solid mounting block
    block = (
        cq.Workplane("XY")
        .box(finger_w, base_len, body_h, centered=(True, False, False))
    )
    body = body.union(block)
    # distal solid cap
    cap = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, finger_len - 6.0, 0))
        .box(finger_w, 6.0, body_h, centered=(True, True, False))
    )
    body = body.union(cap)
    return body


def build_bellows_finger():
    """Full ribbed bending finger with an internal air chamber that opens to the
    proximal (base, -Y) face and a barbed 4/6 mm air port on that face."""
    body = _bellows_body()

    # Internal air chamber: a long pocket running most of the finger, OPEN at the
    # proximal (-Y) face (so it vents to outside → no trapped void). Cut from the
    # front face inward, stopping short of the distal cap.
    ch_h = min(body_h - wall - base_h, body_h * 0.5)
    ch_h = max(3.0, ch_h)
    ch_len = finger_len - base_len * 0.2 - 8.0
    chamber = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -0.5, base_h + wall))
        .box(chamber_w, ch_len, ch_h, centered=(True, False, False))
    )
    body = body.cut(chamber)

    # Barbed air port on the proximal (-Y) face, feeding the chamber. Built as a
    # stepped barb sticking out in -Y, with a through bore into the chamber.
    barb_len = 9.0
    port = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, base_h + wall + ch_h * 0.4, 0))
        .circle(barb_od / 2.0)
        .extrude(barb_len)  # extrudes toward -Y
    )
    # barb ridge (bigger lip near the tip for tube retention)
    ridge = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, base_h + wall + ch_h * 0.4, barb_len - 2.5))
        .circle(barb_od / 2.0 + 0.9)
        .extrude(1.6)
    )
    body = body.union(port).union(ridge)
    # bore through the barb into the chamber
    bore = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, base_h + wall + ch_h * 0.4, -1.0))
        .circle(barb_id / 2.0)
        .extrude(barb_len + 6.0)
    )
    body = body.cut(bore)
    return body


def build_finger_tip():
    """A solid rounded grip cap that slips over the finger's distal end — a
    reprintable fingertip / wear pad master. Hollow socket opens to -Y (the face
    that meets the finger) so no trapped void. Wall thicknesses are floored so the
    socket never severs the cap at extreme small sizes."""
    cap_len = 18.0
    # Fillet the blank BEFORE cutting the socket (fillet-on-blank rule). Keep the
    # fillet radius safely below half the smallest dimension.
    fr = max(1.0, min(2.0, finger_w / 4.0, body_h / 4.0))
    cap = (
        cq.Workplane("XY")
        .box(finger_w, cap_len, body_h, centered=(True, False, False))
    )
    try:
        cap = cap.edges("|Z").fillet(fr)
    except Exception:
        pass

    # Socket for the finger's distal cap, open at the -Y (proximal) face. Floor
    # every wall at >= 1.2 mm so a solid roof/floor/sides always remain: the
    # socket sits ON the base plane (z=0) and its roof leaves >= wall of material.
    sw = max(1.2, wall)
    sock_w = max(2.0, finger_w - 2.0 * sw)
    sock_h = max(2.0, body_h - 2.0 * sw)          # solid floor AND roof of >= sw
    sock = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -0.5, sw))
        .box(sock_w, cap_len - 5.0, sock_h, centered=(True, False, False))
    )
    cap = cap.cut(sock)

    # Friction ribs across the closed (+Y) grip end, over solid material only.
    rib_w = max(2.0, finger_w - 3.0)
    for i in range(4):
        gy = (cap_len - 5.0) + i * 1.0   # all beyond the socket span → solid roof
        gy = min(gy, cap_len - 0.8)
        rib = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, gy, body_h))
            .box(rib_w, 0.9, 1.2, centered=(True, True, False))
        )
        cap = cap.union(rib)
    return cap


def build_base_port():
    """The proximal mounting flange only: a block with the barbed 4/6 mm port and
    two M3 screw ears — bond a finger onto it for a modular soft hand."""
    flange_h = 10.0
    ear = 8.0
    # Fillet the blank block BEFORE any feature cuts (fillet-on-blank rule).
    block = (
        cq.Workplane("XY")
        .box(finger_w, base_len, flange_h, centered=(True, False, False))
    )
    try:
        block = block.edges("|Z").fillet(2.0)
    except Exception:
        pass
    # screw ears left/right — one continuous slab wider than the block, same
    # base_h height, fully overlapping the block so the weld is solid.
    ears = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, base_len / 2.0, 0))
        .box(finger_w + 2.0 * ear, base_len * 0.7, base_h, centered=(True, True, False))
    )
    try:
        ears = ears.edges("|Z").fillet(2.5)
    except Exception:
        pass
    body = block.union(ears)

    # M3 holes in the ears (through the base_h slab, vented top & bottom).
    for sx in (-1, 1):
        hx = sx * (finger_w / 2.0 + ear / 2.0)
        hole = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(hx, base_len / 2.0, -1.0))
            .circle(ear_screw_d / 2.0)
            .extrude(base_h + 2.0)
        )
        body = body.cut(hole)

    # Barbed air port on the -Y face, well inside the tall block so it is fully
    # enveloped by material. A cylinder grown along +Y from a plane in FRONT of
    # the face, plus a retention ridge, then a through bore vented at both ends.
    barb_len = 9.0
    zc = base_h + (flange_h - base_h) * 0.5   # centre within the tall block only
    # port shaft: start 'barb_len' in front of the face (-Y) and grow back into it
    port = (
        cq.Workplane("XZ")
        .workplane(offset=barb_len)
        .center(0.0, zc)
        .circle(barb_od / 2.0)
        .extrude(-(barb_len + 2.0))
    )
    ridge = (
        cq.Workplane("XZ")
        .workplane(offset=barb_len - 1.0)
        .center(0.0, zc)
        .circle(barb_od / 2.0 + 0.9)
        .extrude(-1.6)
    )
    body = body.union(port).union(ridge)
    # through bore from the barb tip (-Y) all the way through the block (+Y).
    bore = (
        cq.Workplane("XZ")
        .workplane(offset=barb_len + 1.0)
        .center(0.0, zc)
        .circle(barb_id / 2.0)
        .extrude(-(barb_len + base_len + 3.0))
    )
    body = body.cut(bore)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "finger_tip":
    result = build_finger_tip()
elif target_part == "base_port":
    result = build_base_port()
else:
    result = build_bellows_finger()
