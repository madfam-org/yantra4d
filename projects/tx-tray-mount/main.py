"""
TX Tray Mount — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A tray / stand for an RC transmitter (radio). The radio's lower body drops into a
cradle sized to its footprint; a neck-strap loop takes the weight off your hands,
and the whole thing tilts for comfortable viewing. Three modes: a hand tray with
a strap loop, an angled desk stand, and a tray with an added phone clip for a
telemetry / video phone.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `radio_w`).
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
radio_w      = float(PARAM(lambda: radio_w,     160.0))  # radio body width (X)
radio_d      = float(PARAM(lambda: radio_d,      45.0))  # radio body depth front-back (Y)
cradle_h     = float(PARAM(lambda: cradle_h,     30.0))  # how high the cradle walls rise
wall         = float(PARAM(lambda: wall,          3.0))  # cradle wall thickness
radio_clear  = float(PARAM(lambda: radio_clear,   1.0))  # per-side clearance around the radio
tilt         = float(PARAM(lambda: tilt,         20.0))  # viewing tilt angle (deg)
strap_loop   = bool( PARAM(lambda: strap_loop,   True))  # add a neck-strap loop
loop_w       = float(PARAM(lambda: loop_w,       25.0))  # strap loop opening width
stand_depth  = float(PARAM(lambda: stand_depth,  70.0))  # desk-stand foot depth (desk mode)
phone_w      = float(PARAM(lambda: phone_w,      78.0))  # phone width to clip (phone mode)
phone_t      = float(PARAM(lambda: phone_t,      12.0))  # phone thickness (phone mode)

target_part  = str(PARAM(lambda: target_part, "tray"))
# "tray" | "desk_stand" | "phone_mount"


# ── Derived / clamped geometry ───────────────────────────────────────────────
pocket_w = radio_w + 2.0 * radio_clear
pocket_d = radio_d + 2.0 * radio_clear
out_w = pocket_w + 2.0 * wall
out_d = pocket_d + 2.0 * wall
floor_t = max(2.0, wall)
tilt = max(0.0, min(tilt, 45.0))


def _cradle():
    """A walled cradle: outer box minus the radio pocket (open top). The radio's
    lower body seats here. Floor at z=0, walls up to z=cradle_h."""
    outer = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, cradle_h / 2.0))
        .box(out_w, out_d, cradle_h, centered=(True, True, True))
    )
    pocket = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, floor_t + (cradle_h) / 2.0))
        .box(pocket_w, pocket_d, cradle_h, centered=(True, True, True))
    )
    cradle = outer.cut(pocket)
    try:
        cradle = cradle.edges("|Z").fillet(min(4.0, wall + 1.0))
    except Exception:
        pass
    return cradle


def _strap_loop():
    """A loop bar spanning across the back of the cradle for a neck strap. Built
    as a solid arch with the opening cut out, sitting behind the cradle (-Y)."""
    loop_th = max(3.0, wall)
    loop_h = 14.0
    y_back = -out_d / 2.0 - loop_th / 2.0
    outer = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, y_back, cradle_h * 0.5))
        .box(loop_w + 2.0 * loop_th, loop_th, loop_h + 2.0 * loop_th, centered=(True, True, True))
    )
    opening = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, y_back, cradle_h * 0.5))
        .box(loop_w, loop_th + 2.0, loop_h, centered=(True, True, True))
    )
    loop = outer.cut(opening)
    # A short tab connecting the loop to the cradle back wall.
    tab = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -out_d / 2.0 + loop_th / 2.0, cradle_h * 0.5))
        .box(loop_w, loop_th + 1.0, loop_h, centered=(True, True, True))
    )
    return loop.union(tab)


def _wedge_base(depth, rise):
    """An angled wedge base under the cradle that tilts it back by ~`tilt`. The
    top face (where the cradle sits) rises from front to back by `rise` over
    `depth`. Built spanning X = out_w, Y = depth, sitting below z=0."""
    profile = (
        cq.Workplane("XZ")
        .polyline([
            (-depth / 2.0, 0.0),
            (depth / 2.0, 0.0),
            (depth / 2.0, rise),
            (-depth / 2.0, 0.0),
        ])
        .close()
        .extrude(out_w / 2.0, both=True)
    )
    # Reorient: polyline X = depth (front-back) should map to world Y.
    wedge = profile.rotate((0, 0, 0), (0, 0, 1), 90.0)
    # Sit the wedge below z=0 so the cradle floor rests on its high point.
    wedge = wedge.translate((0, 0, -rise))
    return wedge


def build_tray():
    """Hand tray: the cradle, tilted for viewing, plus an optional strap loop."""
    cradle = _cradle()
    if strap_loop:
        cradle = cradle.union(_strap_loop())
    # Tilt the whole tray back about X (top edge toward the pilot).
    if tilt > 0.1:
        cradle = cradle.rotate((0, 0, 0), (1, 0, 0), -tilt)
    return cradle


def build_desk_stand():
    """Desk stand: the cradle on a wedge foot so the radio stands angled on a
    bench for setup / simulator use. No strap loop (it rests on the desk)."""
    rise = out_d * 0.9  # enough rise for a comfortable bench angle
    base = _wedge_base(stand_depth, rise)
    cradle = _cradle()
    # Lift the cradle to the wedge's high (back) point and lean it forward.
    cradle = cradle.rotate((0, 0, 0), (1, 0, 0), -max(tilt, 15.0))
    body = base.union(cradle)
    return body


def build_phone_mount():
    """Tray + a phone clip arm rising from the back so a telemetry / FPV phone
    sits above the radio. The clip is a shallow C-channel sized to the phone."""
    tray = _cradle()
    if strap_loop:
        tray = tray.union(_strap_loop())
    # Phone clip: a back post carrying a shallow channel that grips the phone.
    post_h = cradle_h + 55.0
    post = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -out_d / 2.0 + wall, post_h / 2.0))
        .box(loop_w + 10.0, wall * 1.5, post_h, centered=(True, True, True))
    )
    # Channel at the top of the post (opens toward +Y / front).
    ch_w = phone_w + 2.0
    ch_outer = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -out_d / 2.0 + wall + phone_t / 2.0, post_h - 6.0))
        .box(ch_w + 2.0 * wall, phone_t + 2.0 * wall, 14.0, centered=(True, True, True))
    )
    ch_slot = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -out_d / 2.0 + wall + phone_t / 2.0 + 1.0, post_h - 6.0))
        .box(ch_w, phone_t, 16.0, centered=(True, True, True))
    )
    clip = ch_outer.cut(ch_slot)
    body = tray.union(post).union(clip)
    if tilt > 0.1:
        body = body.rotate((0, 0, 0), (1, 0, 0), -tilt)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "desk_stand":
    result = build_desk_stand()
elif target_part == "phone_mount":
    result = build_phone_mount()
else:  # "tray"
    result = build_tray()
