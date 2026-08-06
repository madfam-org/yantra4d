"""
Hobby Servo Bracket — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Cradles a hobby servo by its body. The cradle is a pocket sized to the servo
(SG90 micro = 23 x 12.2 mm, MG996R standard = 40.7 x 19.7 mm) with a floor window
that clears the output shaft / horn, plus mounting tabs matching the servo's own
flange screws. Pick the servo; the pocket, window and tab holes follow.

Modes (dispatched via `target_part`):
  * "servo_mount"      — a single body cradle: four walls around the servo, a
                         floor with a shaft window, and two flange tabs with the
                         servo's mounting-screw holes.
  * "pan_tilt_bracket" — a base cradle (pan servo) carrying an upright yoke with a
                         second cradle rotated 90° for the tilt servo.
  * "u_bracket"        — a U-shaped output arm: a cross web with two side arms and
                         a boss hole, the classic part a servo horn drives.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `servo`).
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


# ── Servo table (body L x W, mounting) ───────────────────────────────────────
# body_l, body_w: servo body footprint (mm); flange_l: screw-centre spacing along
# the length (mm); screw: flange screw clearance dia (mm); depth: cradle depth (mm).
SERVO_TABLE = {
    "SG90":   {"body_l": 23.0, "body_w": 12.2, "flange_l": 28.0, "screw": 2.2, "depth": 16.0},
    "MG996R": {"body_l": 40.7, "body_w": 19.7, "flange_l": 49.5, "screw": 3.2, "depth": 26.0},
}


def servo_spec(key):
    k = str(key).strip().upper().replace(" ", "").replace("-", "")
    return SERVO_TABLE.get(k, SERVO_TABLE["SG90"])


# ── Parameters ───────────────────────────────────────────────────────────────
servo       = str(  PARAM(lambda: servo,      "SG90"))   # SG90 | MG996R
wall        = float(PARAM(lambda: wall,          2.4))   # cradle wall thickness
floor       = float(PARAM(lambda: floor,         2.5))   # cradle floor thickness
clear       = float(PARAM(lambda: clear,         0.4))   # body-to-wall clearance (print fit)
tab_len     = float(PARAM(lambda: tab_len,       7.0))   # flange tab length beyond the body
arm_len     = float(PARAM(lambda: arm_len,      22.0))   # U-bracket side-arm length
boss_d      = float(PARAM(lambda: boss_d,        6.0))   # U-bracket pivot boss hole dia

target_part = str(  PARAM(lambda: target_part, "servo_mount"))
# "servo_mount" | "pan_tilt_bracket" | "u_bracket"


# ── Derived / clamped geometry ───────────────────────────────────────────────
spec = servo_spec(servo)
body_l = spec["body_l"]
body_w = spec["body_w"]
flange_l = spec["flange_l"]
screw_r = max(0.8, spec["screw"] / 2.0)
depth = spec["depth"]

wall = max(1.6, wall)
floor = max(1.6, floor)
clear = max(0.15, min(clear, 1.0))
pocket_l = body_l + 2.0 * clear
pocket_w = body_w + 2.0 * clear
outer_l = pocket_l + 2.0 * wall
outer_w = pocket_w + 2.0 * wall


# ── Helpers ──────────────────────────────────────────────────────────────────
def _cradle(cradle_depth):
    """An open-top rectangular cradle centred on the origin (base at z=0): outer
    block hollowed to the servo pocket, with a floor window that clears the output
    shaft. Returned as one watertight solid (open top only)."""
    outer = cq.Workplane("XY").box(
        outer_l, outer_w, cradle_depth + floor, centered=(True, True, False)
    )
    # Fillet the vertical corners on the clean outer blank first.
    fr = min(wall, outer_w / 2.0 - 0.5)
    if fr > 0.2:
        outer = outer.edges("|Z").fillet(fr)

    # Hollow the servo pocket from the top (leaves the floor slab).
    pocket = (
        cq.Workplane("XY")
        .box(pocket_l, pocket_w, cradle_depth + 1.0, centered=(True, True, False))
        .translate((0, 0, floor))
    )
    body = outer.cut(pocket)

    # Floor window for the shaft / wiring (through the floor).
    win = (
        cq.Workplane("XY")
        .box(pocket_l * 0.6, pocket_w * 0.6, floor + 2.0, centered=(True, True, False))
        .translate((0, 0, -1.0))
    )
    body = body.cut(win)
    return body


def _flange_tabs(cradle_depth):
    """Two mounting tabs projecting along +X/−X at the servo flange height, each
    with the servo's mounting-screw hole. The tab top sits flush with the cradle
    rim. Returned as a solid (union), holes cut."""
    tab_z_top = cradle_depth + floor
    tab_t = max(2.0, floor)
    tab_z0 = tab_z_top - tab_t
    tab_w = outer_w
    tab_reach = tab_len + wall
    # Screw x-position (flange spacing is measured screw-to-screw across the body).
    sx = flange_l / 2.0
    tabs = None
    for sign in (-1, 1):
        x0 = sign * (outer_l / 2.0)
        # A tab slab hanging off the end.
        slab = (
            cq.Workplane("XY")
            .box(tab_reach, tab_w, tab_t, centered=(False, True, False))
            .translate((x0 if sign > 0 else x0 - tab_reach, 0, tab_z0))
        )
        fr = min(screw_r + 1.5, tab_w / 2.0 - 0.5)
        if fr > 0.2:
            slab = slab.edges("|Z").fillet(fr)
        # Screw hole through the tab.
        hole = (
            cq.Workplane("XY")
            .circle(screw_r)
            .extrude(tab_t + 2.0)
            .translate((sign * sx, 0, tab_z0 - 1.0))
        )
        slab = slab.cut(hole)
        tabs = slab if tabs is None else tabs.union(slab)
    return tabs


# ── Builders ─────────────────────────────────────────────────────────────────
def build_servo_mount():
    """A single body cradle with two flange tabs. The tab slabs overlap the cradle
    walls so the union is one watertight solid."""
    body = _cradle(depth)
    body = body.union(_flange_tabs(depth))
    return body


def build_pan_tilt_bracket():
    """A base (pan) cradle carrying an upright yoke that holds a second cradle
    rotated 90° for the tilt servo. Built from overlapping solids."""
    base = _cradle(depth)

    # Upright yoke walls rising from the base rim on the two long sides.
    yoke_h = depth + floor + max(outer_w, 24.0) * 0.5
    yoke_t = wall + 1.0
    up_z0 = depth + floor
    yoke = None
    for sy in (-1, 1):
        yc = sy * (outer_w / 2.0 - yoke_t / 2.0)
        post = (
            cq.Workplane("XY")
            .box(outer_l * 0.5, yoke_t, yoke_h, centered=(True, True, False))
            .translate((0, yc, up_z0 - 2.0))   # overlap into the base rim
        )
        yoke = post if yoke is None else yoke.union(post)
    body = base.union(yoke)

    # Tilt cradle at the top of the yoke, rotated 90° about X so its opening faces
    # sideways (axis perpendicular to the pan axis).
    tilt = _cradle(depth)
    tilt = tilt.rotate((0, 0, 0), (1, 0, 0), 90.0)
    # After +90° about X, the cradle (z:0..depth+floor) rotates to span −Y..; lift
    # and centre it between the yoke posts at the top.
    tilt = tilt.translate((0, 0, up_z0 - 2.0 + yoke_h - (depth + floor) / 2.0))
    body = body.union(tilt)
    return body


def build_u_bracket():
    """A U-shaped output arm: a cross web with two parallel side arms and a pivot
    boss hole through each arm — the classic bracket a servo horn drives."""
    web_w = outer_w
    web_l = outer_l
    web_t = max(3.0, floor)
    arm_t = max(3.0, wall + 1.0)
    arm_h = arm_len

    # Cross web (the base of the U), a clean filleted blank.
    web = cq.Workplane("XY").box(web_l, web_w, web_t, centered=(True, True, False))
    fr = min(arm_t, web_w / 2.0 - 0.5)
    if fr > 0.2:
        web = web.edges("|Z").fillet(fr)

    # Two side arms rising from the web ends (overlap into the web).
    body = web
    for sx in (-1, 1):
        xc = sx * (web_l / 2.0 - arm_t / 2.0)
        arm = (
            cq.Workplane("XY")
            .box(arm_t, web_w, arm_h + web_t, centered=(True, True, False))
            .translate((xc, 0, 0))
        )
        # Round the free top edge of the arm on the clean arm blank.
        try:
            arm = arm.edges("|Y and >Z").fillet(min(arm_t / 2.0 - 0.2, web_w / 2.0 - 0.2))
        except Exception:
            pass
        body = body.union(arm)

    # Pivot boss hole through both arms (along X).
    boss_r = max(1.0, boss_d / 2.0)
    hole = (
        cq.Workplane("YZ")
        .workplane(offset=-web_l / 2.0 - 1.0)
        .circle(boss_r)
        .extrude(web_l + 2.0)
        .translate((0, 0, web_t + arm_h * 0.7))
    )
    body = body.cut(hole)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "pan_tilt_bracket":
    result = build_pan_tilt_bracket()
elif target_part == "u_bracket":
    result = build_u_bracket()
else:  # "servo_mount"
    result = build_servo_mount()
