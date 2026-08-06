"""
Cable Drag-Chain Mount — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Bolts the end bracket of a cable drag chain (energy chain / cable carrier) to a
frame. The chain end is a small plate with two bolt holes on a known width; this
mount presents those holes and carries its own surface-mounting holes so a
drag-chain run can be anchored at the fixed and moving ends.

Modes (dispatched via `target_part`):
  * "end_bracket"       — a flat plate: the chain-end bolt holes at one end, two
                          surface-mounting holes at the other, to anchor the fixed
                          end of the chain to a base plate.
  * "extrusion_bracket" — an L-foot for a 2020 T-slot extrusion: the chain-end
                          holes on the upstand, M5 T-nut holes in the foot.
  * "moving_end"        — a plate with the chain-end holes plus a slotted mount so
                          the moving end can be tuned along the carriage travel.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `chain_w`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq


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
# Drag-chain end brackets clamp between two bolts a known distance apart across
# the chain width (e.g. 10/15/18 mm series). chain_h is the mounting-plate height.
chain_w     = float(PARAM(lambda: chain_w,      15.0))   # chain-end bolt spacing (across width)
chain_h     = float(PARAM(lambda: chain_h,      12.0))   # chain-end plate height
chain_hole  = float(PARAM(lambda: chain_hole,    3.4))   # chain-end bolt clearance (M3)
plate_t     = float(PARAM(lambda: plate_t,       4.0))   # plate thickness
margin      = float(PARAM(lambda: margin,        5.0))   # material margin around holes
mount_d     = float(PARAM(lambda: mount_d,       4.5))   # surface / T-nut bolt (M4/M5)
slot_len    = float(PARAM(lambda: slot_len,     14.0))   # moving-end adjustment slot travel
foot_len    = float(PARAM(lambda: foot_len,     30.0))   # extrusion foot length

target_part = str(  PARAM(lambda: target_part, "end_bracket"))
# "end_bracket" | "extrusion_bracket" | "moving_end"


# ── Derived / clamped geometry ───────────────────────────────────────────────
plate_t = max(2.5, plate_t)
chain_w = max(6.0, chain_w)
chain_h = max(8.0, chain_h)
chain_r = max(1.2, chain_hole / 2.0)
margin = max(3.0, margin)
mount_r = max(1.5, mount_d / 2.0)
slot_len = max(4.0, slot_len)

plate_w = chain_w + 2.0 * (chain_r + margin)     # plate width across the chain holes


# ── Helpers ──────────────────────────────────────────────────────────────────
def _plate(length, width, thick, fillet_r):
    """A rounded rectangular plate on XY, base at z=0, centred in X/Y, filleted as
    a clean blank (no features yet)."""
    p = cq.Workplane("XY").box(length, width, thick, centered=(True, True, False))
    fr = min(fillet_r, width / 2.0 - 0.5, length / 2.0 - 0.5)
    if fr > 0.2:
        p = p.edges("|Z").fillet(fr)
    return p


def _drill(body, pts, r, thick):
    if not pts or r <= 0.05:
        return body
    cutter = (
        cq.Workplane("XY")
        .pushPoints(pts)
        .circle(r)
        .extrude(thick + 2.0)
        .translate((0, 0, -1.0))
    )
    return body.cut(cutter)


def _slot(body, cx, cy, length, r, thick):
    """Obround slot centred at (cx,cy), running along X."""
    box = (
        cq.Workplane("XY")
        .box(length, 2.0 * r, thick + 2.0, centered=(True, True, False))
        .translate((cx, cy, -1.0))
    )
    body = body.cut(box)
    ends = [(cx - length / 2.0, cy), (cx + length / 2.0, cy)]
    return _drill(body, ends, r, thick)


def _chain_hole_points(cx):
    """The two chain-end bolt holes, centred about x=cx, spaced chain_w in Y."""
    return [(cx, -chain_w / 2.0), (cx, chain_w / 2.0)]


# ── Builders ─────────────────────────────────────────────────────────────────
def build_end_bracket():
    """A flat plate: chain-end holes at one end, two surface-mounting holes at the
    other, to anchor the fixed end to a base."""
    length = 2.0 * (chain_r + margin) + 2.0 * (mount_r + margin) + 14.0
    plate = _plate(length, plate_w, plate_t, chain_r + 2.0)

    cx = -length / 2.0 + (chain_r + margin)
    plate = _drill(plate, _chain_hole_points(cx), chain_r, plate_t)

    mx = length / 2.0 - (mount_r + margin)
    mount_pts = [(mx, -chain_w / 2.0), (mx, chain_w / 2.0)]
    plate = _drill(plate, mount_pts, mount_r, plate_t)
    return plate


def build_extrusion_bracket():
    """An L-foot for a 2020 extrusion: chain-end holes on the vertical upstand,
    M5 T-nut holes on 20 mm centres in the horizontal foot."""
    up_h = chain_h + 2.0 * (chain_r + 2.0)
    foot = _plate(foot_len, plate_w, plate_t, mount_r + 1.0)
    # T-nut holes on 20 mm centres.
    n = max(1, int(foot_len // 20.0))
    if n == 1:
        foot_pts = [(0.0, 0.0)]
    else:
        start = -((n - 1) * 20.0) / 2.0
        foot_pts = [(start + i * 20.0, 0.0) for i in range(n)]
    foot = _drill(foot, foot_pts, mount_r, plate_t)

    # Vertical upstand at the -X end, carrying the chain-end holes.
    up = _plate(up_h, plate_w, plate_t, chain_r + 1.5)
    up = up.rotate((0, 0, 0), (0, 1, 0), 90.0)
    up = up.translate((-foot_len / 2.0 + plate_t / 2.0, 0, up_h / 2.0 + plate_t))
    body = foot.union(up)

    # Chain-end holes through the upstand (holes run along X through its thickness).
    z_c = up_h / 2.0 + plate_t
    hole_cut = (
        cq.Workplane("YZ")
        .workplane(offset=-foot_len / 2.0 - 1.0)
        .pushPoints([(-chain_w / 2.0, z_c), (chain_w / 2.0, z_c)])
        .circle(chain_r)
        .extrude(plate_t + 2.0)
    )
    body = body.cut(hole_cut)
    return body


def build_moving_end():
    """A plate with the chain-end holes plus a lengthwise adjustment slot so the
    moving end can be tuned along the carriage travel."""
    length = 2.0 * (chain_r + margin) + slot_len + 2.0 * (mount_r + 2.0) + 10.0
    plate = _plate(length, plate_w, plate_t, chain_r + 2.0)

    cx = -length / 2.0 + (chain_r + margin)
    plate = _drill(plate, _chain_hole_points(cx), chain_r, plate_t)

    # Single central adjustment slot toward the other end.
    sx = length / 2.0 - (slot_len / 2.0 + mount_r + 3.0)
    plate = _slot(plate, sx, 0.0, slot_len, mount_r, plate_t)
    return plate


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "extrusion_bracket":
    result = build_extrusion_bracket()
elif target_part == "moving_end":
    result = build_moving_end()
else:  # "end_bracket"
    result = build_end_bracket()
