"""
Robot Sensor Mount — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A tilt-adjustable bracket for a small robot sensor board. The board plate carries
the exact mounting-hole pattern of the sensor (VL53L0X ToF ~13 x 25 mm, MPU6050
IMU ~15 x 21 mm with 2 holes, Raspberry Pi camera 25 x 24 mm with 4 holes) plus a
window that clears the sensor / lens, and rides on two arc-slotted ears so the
board can be angled and locked. Pick the sensor; the footprint follows.

Modes (dispatched via `target_part`):
  * "tof_mount" — a VL53L0X time-of-flight board plate (2 holes, small aperture)
                  on the tilt bracket.
  * "imu_mount" — an MPU6050 IMU board plate (2 holes) on the tilt bracket.
  * "cam_mount" — a Raspberry Pi camera board plate (4 holes on 21 x 12.5 mm) with
                  a lens window, on the tilt bracket.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `sensor`).
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


# ── Sensor board table ───────────────────────────────────────────────────────
# board_w x board_h: PCB footprint (mm); holes: [(x,y),...] mounting-hole centres
# relative to the board centre; hole_d: mounting hole dia; win: (w,h) clearance
# window for the sensor/lens (0 → none).
SENSOR_TABLE = {
    "VL53L0X": {
        "board_w": 13.0, "board_h": 25.0, "hole_d": 2.2,
        "holes": [(0.0, 9.5), (0.0, -9.5)],
        "win": (5.0, 5.0),
    },
    "MPU6050": {
        "board_w": 21.0, "board_h": 15.0, "hole_d": 3.0,
        "holes": [(-8.5, 0.0), (8.5, 0.0)],
        "win": (0.0, 0.0),
    },
    "pi-camera": {
        "board_w": 25.0, "board_h": 24.0, "hole_d": 2.2,
        "holes": [(-10.5, 6.25), (10.5, 6.25), (-10.5, -6.25), (10.5, -6.25)],
        "win": (9.0, 9.0),
    },
}


def sensor_spec(key):
    k = str(key).strip().lower().replace(" ", "").replace("_", "-")
    for name, spec in SENSOR_TABLE.items():
        if name.lower() == k:
            return spec
    return SENSOR_TABLE["VL53L0X"]


# ── Parameters ───────────────────────────────────────────────────────────────
sensor      = str(  PARAM(lambda: sensor,   "VL53L0X"))  # VL53L0X | MPU6050 | pi-camera
plate_t     = float(PARAM(lambda: plate_t,       3.0))   # board-plate thickness
margin      = float(PARAM(lambda: margin,        4.0))   # board-plate material margin
base_t      = float(PARAM(lambda: base_t,        4.0))   # base foot thickness
base_len    = float(PARAM(lambda: base_len,     30.0))   # base foot length
ear_h       = float(PARAM(lambda: ear_h,        22.0))   # tilt-ear height (pivot height)
tilt_deg    = float(PARAM(lambda: tilt_deg,     20.0))   # board rake angle
mount_d     = float(PARAM(lambda: mount_d,       4.5))   # base surface bolt (M4)
pivot_d     = float(PARAM(lambda: pivot_d,       3.4))   # tilt pivot / arc-slot bolt (M3)

target_part = str(  PARAM(lambda: target_part, "tof_mount"))
# "tof_mount" | "imu_mount" | "cam_mount"


# ── Derived / clamped geometry ───────────────────────────────────────────────
SENSOR_BY_PART = {"tof_mount": "VL53L0X", "imu_mount": "MPU6050", "cam_mount": "pi-camera"}
# The mode fixes the sensor; the `sensor` param is the label/echo of it.
sensor = SENSOR_BY_PART.get(target_part, sensor)
spec = sensor_spec(sensor)
board_w = spec["board_w"]
board_h = spec["board_h"]
hole_r = max(0.8, spec["hole_d"] / 2.0)
win_w, win_h = spec["win"]

plate_t = max(2.0, plate_t)
margin = max(3.0, margin)
base_t = max(2.5, base_t)
base_len = max(20.0, base_len)
ear_h = max(12.0, ear_h)
tilt_deg = max(0.0, min(tilt_deg, 45.0))
mount_r = max(1.5, mount_d / 2.0)
pivot_r = max(1.2, pivot_d / 2.0)

plate_w = board_w + 2.0 * (hole_r + margin)      # board-plate footprint (X)
plate_h = board_h + 2.0 * (hole_r + margin)      # board-plate footprint (Y)


# ── Helpers ──────────────────────────────────────────────────────────────────
def _board_plate():
    """The sensor board plate as a flat slab on XY (base at z=0), centred in X/Y,
    carrying the sensor's mounting-hole pattern and its clearance window. `board_h`
    runs along Y, `board_w` along X (before the plate is stood up)."""
    plate = cq.Workplane("XY").box(plate_w, plate_h, plate_t, centered=(True, True, False))
    fr = min(hole_r + 1.5, plate_w / 2.0 - 0.5, plate_h / 2.0 - 0.5)
    if fr > 0.2:
        plate = plate.edges("|Z").fillet(fr)

    # Sensor mounting holes (grouped) — matches the board's hole pattern.
    pts = list(spec["holes"])
    plate = plate.cut(
        cq.Workplane("XY").pushPoints(pts).circle(hole_r)
        .extrude(plate_t + 2.0).translate((0, 0, -1.0))
    )
    # Clearance window for the sensor / lens.
    if win_w > 0.1 and win_h > 0.1:
        plate = plate.cut(
            cq.Workplane("XY")
            .box(win_w, win_h, plate_t + 2.0, centered=(True, True, False))
            .translate((0, 0, -1.0))
        )
    return plate


def _tilt_slot(body, cx, z0, z1, r_slot, thick):
    """Cut a vertical obround adjustment slot through the central pillar (a box
    plus rounded ends), from z0 to z1 at x=cx, spanning the pillar's Y thickness.
    A single clean box + two circle cuts — robust for OCCT (no self-intersecting
    fan). The pillar is centred at Y=0, so the cutter is offset across it."""
    length = abs(z1 - z0)
    zc = (z0 + z1) / 2.0
    box = (
        cq.Workplane("XZ")
        .workplane(offset=thick / 2.0 + 1.0)
        .center(cx, zc)
        .rect(2.0 * r_slot, length)
        .extrude(-(thick + 2.0))
    )
    body = body.cut(box)
    ends = (
        cq.Workplane("XZ")
        .workplane(offset=thick / 2.0 + 1.0)
        .pushPoints([(cx, z0), (cx, z1)])
        .circle(r_slot)
        .extrude(-(thick + 2.0))
    )
    body = body.cut(ends)
    return body


# ── Builders ─────────────────────────────────────────────────────────────────
def build_mount():
    """The tilt bracket for the current sensor: a base foot (surface bolt holes), a
    central pillar rising from it, and the sensor board plate mounted to the front
    of the pillar and raked by `tilt_deg`. The board plate overlaps the pillar (both
    centred on Y=0) so the union is one connected, watertight solid; a curved
    adjustment slot through the pillar carries the tilt-lock bolt."""
    pillar_w = max(plate_w * 0.5, 10.0)                # pillar Y-width
    pillar_x = max(plate_t + 3.0, 6.0)                 # pillar X-depth
    base_w = plate_w + 2.0 * max(mount_r + 3.0, 4.0)   # foot wider than the plate
    top_z = base_t + ear_h

    # Base foot (clean blank), then two surface bolt holes.
    base = cq.Workplane("XY").box(base_len, base_w, base_t, centered=(True, True, False))
    fr = min(mount_r + 1.5, base_w / 2.0 - 0.5, base_len / 2.0 - 0.5)
    if fr > 0.2:
        base = base.edges("|Z").fillet(fr)
    bx = base_len / 2.0 - (mount_r + 3.0)
    base = base.cut(
        cq.Workplane("XY").pushPoints([(-bx, 0.0), (bx, 0.0)]).circle(mount_r)
        .extrude(base_t + 2.0).translate((0, 0, -1.0))
    )

    # Central pillar rising from the base (overlaps the base slab), sitting toward
    # the −X side so the board plate faces +X.
    pillar = (
        cq.Workplane("XY")
        .box(pillar_x, pillar_w, ear_h + base_t, centered=(True, True, False))
        .translate((-pillar_x * 0.5, 0, 0))
    )
    body = base.union(pillar)

    # Board plate: stand it up (thin in X), rake about Y by tilt_deg, and set its
    # lower-back edge overlapping the pillar's front face + top.
    plate = _board_plate()
    plate = plate.rotate((0, 0, 0), (0, 1, 0), 90.0)      # thin in X now
    plate = plate.rotate((0, 0, 0), (0, 1, 0), -tilt_deg)  # rake back
    # Front face of the pillar is at x≈0; place the plate just into it, its centre
    # around the pillar top so the bottom edge overlaps the pillar.
    plate = plate.translate((plate_t * 0.5, 0, top_z - plate_h * 0.5 * math.cos(
        math.radians(tilt_deg)) + 1.0))
    body = body.union(plate)

    # Vertical adjustment slot through the pillar: the frame bolt rides it to set
    # the sensor height / effective angle, then locks.
    slot_z0 = base_t + ear_h * 0.20
    slot_z1 = base_t + ear_h * 0.80
    body = _tilt_slot(body, 0.0, slot_z0, slot_z1, pivot_r, pillar_w)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
# All three modes share the tilt bracket; the mode selects the sensor footprint.
result = build_mount()
