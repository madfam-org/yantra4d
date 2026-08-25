"""
Drill Press Fence — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A drill-press fence with a flip stop for repeatable hole spacing. The fence
clamps to the table's 3/4 in T-track and carries its own top channel that a flip
stop slides along; flip the stop up and the workpiece slides past for the next
position, flip it down to register. The MATING interface is the standard 3/4 in
T-track (shared with bench-dog / featherboard) so the fence bolts to any
track-equipped drill or router table.

T-track / stud reference (3/4 in standard):
  slot mouth = 3/4 in = 19.05 mm    stud = 1/4-20 (≈ 6.6 mm clearance)

Modes (dispatched via `target_part`):
  * "fence_body"    — the fence face: a tall bar with a fore/aft mount slot for
                      the table stud and an open top channel for the stop.
  * "flip_stop"     — an L stop that pivots up/down on a pin and locks to the
                      fence's top channel through a stud slot.
  * "mount_bracket" — a foot bracket that clamps the fence down onto the table's
                      3/4 in T-track through a stud hole.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as BARE globals.
  - Read them via PARAM(lambda: <name>, <default>) — no globals()/eval/getattr.
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


# ── T-track / stud constants (3/4 in standard) ───────────────────────────────
TRACK_SLOT = 19.05
STUD_TABLE = {"1/4-20": 6.6, "5/16-18": 8.4, "M6": 6.6, "M8": 8.6}


def stud_clear(key):
    return STUD_TABLE.get(str(key).strip(), STUD_TABLE["1/4-20"])


# ── Parameters ───────────────────────────────────────────────────────────────
stud        = str(  PARAM(lambda: stud,       "1/4-20"))   # table stud thread
fence_len   = float(PARAM(lambda: fence_len,   180.0))     # fence face length (mm)
fence_h     = float(PARAM(lambda: fence_h,      45.0))     # fence face height (mm)
fence_t     = float(PARAM(lambda: fence_t,      12.0))     # fence face thickness (mm)
channel_w   = float(PARAM(lambda: channel_w,    10.0))     # top stop-channel width (mm)
mount_slot  = float(PARAM(lambda: mount_slot,   40.0))     # table mount slot travel (mm)
stop_h      = float(PARAM(lambda: stop_h,       30.0))     # flip-stop face height (mm)

target_part = str(PARAM(lambda: target_part, "fence_body"))  # fence_body|flip_stop|mount_bracket


# ── Derived / clamped geometry ───────────────────────────────────────────────
stud_d = stud_clear(stud)
fence_len = max(80.0, min(fence_len, 400.0))
fence_h = max(25.0, min(fence_h, 100.0))
fence_t = max(8.0, min(fence_t, 25.0))
channel_w = max(6.0, min(channel_w, fence_t - 2.0))
mount_slot = max(stud_d + 6.0, min(mount_slot, fence_len - 20.0))
stop_h = max(15.0, min(stop_h, 80.0))


# ── Helpers ──────────────────────────────────────────────────────────────────
def _slot_z(body, cx, cy, length, dia, total_h, z0):
    """Vertical obround slot (native slot2D — one closed wire, watertight) bored
    through the body along Z, centred at (cx, cy)."""
    slot = (
        cq.Workplane("XY")
        .slot2D(max(dia + 0.01, length), dia, angle=0)
        .extrude(total_h + 2.0)
        .translate((cx, cy, z0 - 1.0))
    )
    return body.cut(slot)


# ── Builders ─────────────────────────────────────────────────────────────────
def build_fence_body():
    """A tall fence bar. Along the top runs an open stop-channel (a rectangular
    groove the flip stop slides in). Two fore/aft mount slots at the base let a
    table stud clamp the fence to the T-track."""
    body = cq.Workplane("XY").box(fence_len, fence_t, fence_h, centered=(True, True, False))
    # Open top channel: a rectangular groove down from the top face, running the
    # full length (open at both ends → not a trapped void).
    ch_depth = min(fence_h * 0.3, channel_w * 1.2)
    channel = (
        cq.Workplane("XY")
        .box(fence_len + 2.0, channel_w, ch_depth + 0.02, centered=(True, True, False))
        .translate((0, 0, fence_h - ch_depth))
    )
    body = body.cut(channel)
    # Two table-mount slots near the base ends (vertical obround through the base).
    off = fence_len / 2.0 - mount_slot / 2.0 - 6.0
    for sx in (-off, off):
        body = _slot_z(body, sx, 0.0, mount_slot, stud_d, fence_h * 0.4, 0.0)
    # Ease the top outer edges.
    try:
        body = body.edges("|X and >Z").fillet(min(2.0, fence_t * 0.15))
    except Exception:
        pass
    return body


def build_flip_stop():
    """An L flip stop: a base that sits in the fence top channel with a stud slot
    to lock it, and an upstanding stop face the workpiece butts against. A pivot
    pin hole lets it flip up out of the way."""
    base_len = 34.0
    base_t = 8.0
    base_w = max(channel_w + 6.0, 16.0)
    base = cq.Workplane("XY").box(base_len, base_w, base_t, centered=(True, True, False))
    # Upstanding stop face (the register surface) at the +X end.
    face = (
        cq.Workplane("XY")
        .box(6.0, base_w, stop_h, centered=(False, True, False))
        .translate((base_len / 2.0 - 6.0, 0, 0))
    )
    body = base.union(face)
    # Gusset.
    web = (
        cq.Workplane("XZ")
        .workplane(offset=base_w / 2.0)
        .polyline([(base_len / 2.0 - 6.0, base_t),
                   (base_len / 2.0 - 6.0, stop_h * 0.6),
                   (base_len / 2.0 - 6.0 - stop_h * 0.4, base_t)])
        .close()
        .extrude(-base_w)
    )
    body = body.union(web)
    # Locking stud slot through the base.
    body = _slot_z(body, -6.0, 0.0, 14.0, stud_d, base_t, 0.0)
    # Pivot pin hole (cross the base along Y near the back).
    pin = (
        cq.Workplane("XZ")
        .workplane(offset=base_w / 2.0 + 0.5)
        .circle(2.6)
        .extrude(-(base_w + 1.0))
        .translate((-base_len / 2.0 + 5.0, 0, base_t / 2.0))
    )
    body = body.cut(pin)
    return body


def build_mount_bracket():
    """A foot bracket clamping the fence down onto the table T-track: a base with
    a stud hole to the track and an upstand that bolts to the fence end."""
    t = 8.0
    base_len = 46.0
    base_w = max(TRACK_SLOT + 6.0, 26.0)
    base = cq.Workplane("XY").box(base_len, base_w, t, centered=(False, True, False))
    upstand = (
        cq.Workplane("XY")
        .box(t, base_w, fence_h * 0.7, centered=(False, True, False))
        .translate((base_len - t, 0, 0))
    )
    body = base.union(upstand)
    web = (
        cq.Workplane("XZ")
        .workplane(offset=base_w / 2.0)
        .polyline([(base_len - t, t), (base_len - t, fence_h * 0.5),
                   (base_len - t - fence_h * 0.35, t)])
        .close()
        .extrude(-base_w)
    )
    body = body.union(web)
    # Track stud hole through the base.
    hole = cq.Workplane("XY").cylinder(t + 2.0, stud_d / 2.0).translate((base_len * 0.4, 0, t / 2.0))
    body = body.cut(hole)
    # Two fence bolts through the upstand (bored along +X).
    for sz in (fence_h * 0.25, fence_h * 0.5):
        b = (
            cq.Workplane("YZ")
            .workplane(offset=base_len - t - 0.5)
            .circle(stud_d / 2.0)
            .extrude(t + 1.0)
            .translate((0, 0, sz))
        )
        body = body.cut(b)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "flip_stop":
    result = build_flip_stop()
elif target_part == "mount_bracket":
    result = build_mount_bracket()
else:
    result = build_fence_body()
