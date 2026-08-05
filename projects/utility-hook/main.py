"""
Utility Hook / Coat Peg — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A wall hook for coats, bags, towels, keys, or utility items. The hook is a
forward reach with an upward curl at the tip so items cannot slide off; a
selectable mount fixes it to a wall, a smooth surface, or over a door.

Two parts (dispatched through `target_part`):
  * "hook"       — a single hook on the selected mount.
  * "hook_rail"  — a horizontal rail carrying `count` hooks on one back plate.

Mount types (`mount_type`):
  * "screw"     — a flat back plate with two countersunk-friendly screw holes.
  * "adhesive"  — a flat back plate (foam adhesive tape goes on its back face);
                  no holes.
  * "over_door" — the back plate turns 180° over the top of a door of
                  `door_thick`, hanging without any fixings.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `hook_reach`).
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


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "hook"))    # hook | hook_rail
mount_type = str(PARAM(lambda: mount_type, "screw"))     # screw | adhesive | over_door

hook_reach = float(PARAM(lambda: hook_reach, 40.0))      # forward projection to the curl
hook_curl_r = float(PARAM(lambda: hook_curl_r, 12.0))    # radius of the up-curl at the tip
hook_thick = float(PARAM(lambda: hook_thick, 8.0))       # hook stock thickness (load)
hook_width = float(PARAM(lambda: hook_width, 12.0))      # hook stock width (across)

plate_thick = float(PARAM(lambda: plate_thick, 5.0))     # back-plate thickness
plate_w = float(PARAM(lambda: plate_w, 26.0))            # back-plate width
plate_h = float(PARAM(lambda: plate_h, 45.0))            # back-plate height
screw_dia = float(PARAM(lambda: screw_dia, 4.5))         # screw clearance hole

door_thick = float(PARAM(lambda: door_thick, 40.0))      # door leaf thickness (over-door)

count = int(PARAM(lambda: count, 3))                     # hooks on a rail
spacing = float(PARAM(lambda: spacing, 60.0))            # hook centre spacing (rail)

# Sanitize
hook_thick = max(3.0, hook_thick)
hook_width = max(4.0, hook_width)
plate_thick = max(3.0, plate_thick)
count = max(2, min(8, count))


# ── Hook geometry ─────────────────────────────────────────────────────────────
def _hook_arm():
    """A single hook arm growing forward (-Y) from the plate front (y=0), then
    curling upward (+Z) at the tip so items cannot slide off. Built from a
    horizontal bar + a quarter-torus curl (a revolved rectangular section) +
    a short vertical finger, all unioned. Centred on X=0, root at z=0.

    Returns the arm solid; the caller translates it to the desired X and Z."""
    reach = max(hook_curl_r + hook_thick, hook_reach)
    r = max(hook_thick * 0.6, min(hook_curl_r, reach - hook_thick * 1.5))
    sec_w = hook_width
    sec_t = hook_thick

    # 1) Horizontal bar from the plate front forward to the curl start, with a
    #    2 mm overlap back into the plate for a clean union.
    overlap = 2.0
    curl_start_y = -(reach - r)
    bar_len = (r - reach) * -1.0 + overlap        # == reach - r + overlap
    bar = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, curl_start_y / 2.0 + overlap / 2.0, 0))
        .box(sec_w, bar_len, sec_t, centered=(True, True, True))
    )

    # 2) Quarter-torus curl: revolve the rectangular section 90° about an axis
    #    parallel to X passing through (y=curl_start_y, z=r). The section sits
    #    at radius r from that axis, starting pointing -Y and ending +Z.
    curl = _quarter_curl(curl_start_y, r, sec_w, sec_t)

    # 3) Short vertical finger at the tip that captures the item.
    finger_h = max(hook_thick, r * 0.8)
    tip_y = curl_start_y
    finger = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, tip_y, r + finger_h / 2.0 - 0.01))
        .box(sec_w, sec_t, finger_h, centered=(True, True, True))
    )
    arm = bar.union(curl).union(finger)
    return arm


def _quarter_curl(cy, r, sec_w, sec_t):
    """A quarter-turn curl of a sec_w × sec_t rectangular section, turning from
    horizontal (open toward -Y) up to vertical (+Z). The bend centre axis is
    parallel to X at (y=cy, z=r). Built as a union of short prisms sampled along
    the arc — robust and watertight for any radius. The centreline runs:
        y(a) = cy + r*sin(a),   z(a) = r - r*cos(a),   a ∈ [0, 90°]
    so a=0 is at (cy, 0) tangent to the bar and a=90° is at (cy+r, r)… the tip
    ends above the curl start, pointing up."""
    segs = 14
    step = (math.pi / 2.0) / segs
    parts = None
    for i in range(segs):
        a = (i + 0.5) * step
        y = cy + r * math.sin(a)
        z = r - r * math.cos(a)
        # Segment length along the arc, plus a hair of overlap between prisms.
        seg_len = r * step * 1.35 + 0.2
        node = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, y, z))
            .transformed(rotate=cq.Vector(math.degrees(a), 0, 0))
            .box(sec_w, sec_t, seg_len, centered=(True, True, True))
        )
        parts = node if parts is None else parts.union(node)
    return parts


# ── Plates / mounts ───────────────────────────────────────────────────────────
def _back_plate(width, height):
    """Flat wall plate: front face at y=0, thickness toward -Y, base at z=0."""
    plate = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -plate_thick, 0))
        .box(width, plate_thick, height, centered=(True, True, False))
    )
    try:
        plate = plate.edges("|Y").fillet(min(width / 4.0, height / 6.0, 5.0))
    except Exception:
        pass
    return plate


def _drill_screws(plate, xs, height):
    r = screw_dia / 2.0
    if mount_type != "screw" or r <= 0.05:
        return plate
    zs = [max(r + 4.0, 8.0), height - max(r + 4.0, 8.0)]
    if zs[1] - zs[0] < 5.0:
        zs = [height / 2.0]
    for x in xs:
        for z in zs:
            bore = (
                cq.Workplane("XZ")
                .center(x, z)
                .circle(r)
                .extrude(-(plate_thick + 2.0))
                .translate((0, 1.0, 0))
            )
            plate = plate.cut(bore)
    return plate


def _over_door_yoke(width, height):
    """An over-door yoke: the front plate (y:0→-plate_thick), a top bridge across
    the door top, and a short rear lip down the back of the door. The door
    occupies y ∈ [-plate_thick - gap - door_thick, -plate_thick - gap]."""
    gap = 2.0
    dt = max(6.0, door_thick)
    front = _back_plate(width, height)

    top_z = height
    # Top bridge over the door: spans from the front plate back over the door.
    bridge_len = plate_thick + gap + dt + gap + plate_thick
    bridge = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -bridge_len + plate_thick, top_z))
        .box(width, bridge_len, plate_thick, centered=(True, True, False))
    )
    # Rear lip hanging down the back of the door.
    rear_y = -(plate_thick + gap + dt + gap)
    lip_h = min(height * 0.6, 40.0)
    rear = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, rear_y, top_z - lip_h))
        .box(width, plate_thick, lip_h, centered=(True, True, False))
    )
    yoke = front.union(bridge).union(rear)
    return yoke


def _mount(width, height, xs):
    if mount_type == "over_door":
        return _over_door_yoke(width, height)
    plate = _back_plate(width, height)
    plate = _drill_screws(plate, xs, height)
    return plate


# ── Part builders ─────────────────────────────────────────────────────────────
def _hook_z(height):
    """Vertical position of the hook root on the plate (lower third)."""
    return min(height * 0.32, height - hook_curl_r - hook_thick)


def build_hook():
    width = max(plate_w, hook_width + 8.0)
    height = max(plate_h, hook_curl_r + hook_thick + 16.0)
    body = _mount(width, height, [0.0])
    z_root = _hook_z(height)
    arm = _hook_arm().translate((0, 0, z_root))
    body = body.union(arm)
    return body


def build_hook_rail():
    pitch = max(hook_width + 12.0, spacing)
    width = (count - 1) * pitch + max(hook_width + 8.0, 20.0)
    height = max(plate_h, hook_curl_r + hook_thick + 16.0)
    x0 = -(count - 1) * pitch / 2.0
    xs = [x0 + i * pitch for i in range(count)]

    body = _mount(width, height, xs)
    z_root = _hook_z(height)
    for x in xs:
        arm = _hook_arm().translate((x, 0, z_root))
        body = body.union(arm)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "hook_rail":
    result = build_hook_rail()
else:
    result = build_hook()
