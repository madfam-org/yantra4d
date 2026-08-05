"""
Bike Accessory Mount — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A two-piece bolt clamp that grips a bicycle handlebar and carries an accessory on
top. The handlebar saddle is sized to the ISO grip/bar standards (22.2 / 25.4 /
31.8 mm) and the accessory side is one of the ubiquitous action-cam / camera /
light interfaces.

Three parts (dispatched via `target_part`):
  * "gopro_mount"     — clamp base + a GoPro-style two-finger clevis on top.
  * "quarter20_mount" — clamp base + a 1/4-20 camera boss/socket pad on top.
  * "strap_mount"     — clamp base + a strap/loop bracket (or a plain tab) on top.

The clamp is TWO printed halves: the accessory-carrying base half (with a
semicircular saddle and two bolt ears) and a matching cap half; two bolts pull
them together around the bar. Both halves render in one part so the clamp prints
as a pair.

GoPro finger spec: thickness ~3.0 mm, gap ~3.2 mm, 5 mm pivot hole.
1/4-20 boss: 6.35 mm nominal major diameter (cosmetic ~5.5 mm bore for the socket).

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `bar_dia`).
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


# ── Handlebar standards (nominal diameters, mm) ──────────────────────────────
BAR_DIAMETERS = {
    "22.2": 22.2,   # standard grip / control-clamp diameter
    "25.4": 25.4,   # 1" bars
    "31.8": 31.8,   # oversized clamp diameter
}


def bar_diameter(key):
    return BAR_DIAMETERS.get(str(key).strip(), 22.2)


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "gopro_mount"))  # gopro_mount|quarter20_mount|strap_mount
bar_dia     = str(PARAM(lambda: bar_dia,      "22.2"))         # handlebar diameter standard
interface   = str(PARAM(lambda: interface,    "gopro"))        # gopro | 1/4-20 | phone_tab | light

clamp_w     = float(PARAM(lambda: clamp_w,     16.0))          # clamp width along the bar (mm)
wall        = float(PARAM(lambda: wall,         4.0))          # material around the saddle (mm)
bolt_dia    = float(PARAM(lambda: bolt_dia,     4.3))          # clamp bolt clearance (M4)
grip_pad    = float(PARAM(lambda: grip_pad,     0.3))          # radial squeeze (saddle smaller than bar)
phone_w     = float(PARAM(lambda: phone_w,     70.0))          # phone/accessory width for tab (mm)

# Clamp inputs to sane ranges so extreme UI values still build watertight.
clamp_w  = max(8.0, min(clamp_w, 40.0))
wall     = max(2.5, min(wall, 10.0))
bolt_dia = max(2.0, min(bolt_dia, 8.0))
grip_pad = max(0.0, min(grip_pad, 1.0))
phone_w  = max(40.0, min(phone_w, 100.0))

BAR_D = bar_diameter(bar_dia)
BAR_R = BAR_D / 2.0
SADDLE_R = max(3.0, BAR_R - grip_pad)          # saddle grips slightly tighter than the bar
BLOCK_R = SADDLE_R + wall                        # outer radius of the clamp body
EAR_LEN = bolt_dia * 1.6 + 4.0                   # how far the bolt ears stick out each side
FINGER_T = 3.0                                   # GoPro finger thickness
FINGER_GAP = 3.2                                 # GoPro finger gap
PIVOT_D = 5.0                                    # GoPro pivot hole


# ── Clamp half primitives ────────────────────────────────────────────────────
def _clamp_ears(z_lo, z_hi):
    """Two bolt ears bridging the split plane (at z between the halves), each with a
    through bolt hole. Ears extend in ±X beyond the round body."""
    ear_th = z_hi - z_lo
    x_out = BLOCK_R + EAR_LEN
    ear = (
        cq.Workplane("XY")
        .box(2.0 * x_out, clamp_w, ear_th, centered=(True, True, False))
        .translate((0, 0, z_lo))
    )
    # Remove the central round body zone so the ears are just the outboard tabs;
    # the body itself is added separately.
    keep_body = cq.Workplane("XY").cylinder(ear_th + 2.0, BLOCK_R, centered=(True, True, False)).translate((0, 0, z_lo - 1.0))
    ear = ear.cut(keep_body)
    # Bolt holes through both ears.
    bx = BLOCK_R + EAR_LEN / 2.0
    holes = (
        cq.Workplane("XY")
        .pushPoints([(-bx, 0.0), (bx, 0.0)])
        .circle(bolt_dia / 2.0)
        .extrude(ear_th + 2.0)
        .translate((0, 0, z_lo - 1.0))
    )
    ear = ear.cut(holes)
    return ear


def build_clamp_base():
    """Lower clamp half: the accessory-carrying half. A half-cylinder body with a
    semicircular saddle cut from its TOP, plus bolt ears at the split plane.

    Returns (solid, top_z) where top_z is the flat top surface the accessory sits on.
    The body occupies z:[0, top_z]; the saddle is a half-bore centred at z=top_z."""
    body_h = BLOCK_R                              # from base plane up to the split (bar centre)
    # Solid half-cylinder (a full cylinder trimmed to the lower half in Y is awkward;
    # instead build a block and round it). Use a rounded rectangular body so the flat
    # top gives a clean accessory pad.
    body = (
        cq.Workplane("XY")
        .box(2.0 * BLOCK_R, clamp_w, body_h, centered=(True, True, False))
    )
    try:
        body = body.edges("|Y and <Z").fillet(min(BLOCK_R * 0.6, body_h - 0.5))
    except Exception:
        pass
    # Saddle: a half-cylinder cavity opening upward, axis along Y at z = body_h.
    saddle = (
        cq.Workplane("XZ")
        .circle(SADDLE_R)
        .extrude(clamp_w / 2.0, both=True)
        .translate((0, 0, body_h))
    )
    body = body.cut(saddle)
    body = body.union(_clamp_ears(0.0, body_h))
    return body, body_h


def build_clamp_cap(y_offset):
    """Upper clamp half, mirrored, placed offset in +Y so it prints alongside the
    base rather than overlapping it. Same saddle + ears."""
    body_h = BLOCK_R
    body = (
        cq.Workplane("XY")
        .box(2.0 * BLOCK_R, clamp_w, body_h, centered=(True, True, False))
    )
    try:
        body = body.edges("|Y and >Z").fillet(min(BLOCK_R * 0.6, body_h - 0.5))
    except Exception:
        pass
    saddle = (
        cq.Workplane("XZ")
        .circle(SADDLE_R)
        .extrude(clamp_w / 2.0, both=True)
        .translate((0, 0, 0.0))
    )
    body = body.cut(saddle)
    body = body.union(_clamp_ears(0.0, body_h))
    # Sit the cap next to the base along Y for a printable pair layout.
    return body.translate((0, y_offset, 0))


# ── Accessory interfaces (built on top of the base half) ─────────────────────
def _gopro_clevis(top_z):
    """A GoPro-style two-finger clevis rising from the pad top. Two fingers on the
    standard pitch with a 5 mm pivot hole through them."""
    reach = 10.0                                  # how far the fingers rise
    knuckle_r = PIVOT_D / 2.0 + 2.2
    pitch = FINGER_T + FINGER_GAP
    xs = [-pitch / 2.0, pitch / 2.0]
    fingers = None
    for x in xs:
        shaft = (
            cq.Workplane("XY")
            .box(FINGER_T, knuckle_r * 2.0, reach, centered=(True, True, False))
            .translate((x, 0, top_z))
        )
        knuckle = (
            cq.Workplane("XZ")
            .circle(knuckle_r)
            .extrude(FINGER_T / 2.0, both=True)
            .translate((x, 0, top_z + reach))
        )
        f = shaft.union(knuckle)
        fingers = f if fingers is None else fingers.union(f)
    # Pivot hole through both fingers (axis along X).
    hole = (
        cq.Workplane("YZ")
        .circle(PIVOT_D / 2.0)
        .extrude(pitch * 2.0, both=True)
        .translate((0, 0, top_z + reach))
    )
    fingers = fingers.cut(hole)
    return fingers


def _quarter20_pad(top_z):
    """A 1/4-20 camera pad: a raised boss with a cosmetic ~5.5 mm socket bore (the
    printed thread envelope for a 6.35 mm 1/4-20 screw)."""
    boss_r = 8.0
    boss_h = 8.0
    boss = (
        cq.Workplane("XY")
        .cylinder(boss_h, boss_r, centered=(True, True, False))
        .translate((0, 0, top_z))
    )
    # Cosmetic socket bore (not a slow helix): a straight bore at the 1/4-20 minor-ish
    # envelope, plus a lead-in chamfer.
    bore = (
        cq.Workplane("XY")
        .circle(5.5 / 2.0)
        .extrude(boss_h + 1.0)
        .translate((0, 0, top_z - 0.5))
    )
    boss = boss.cut(bore)
    try:
        boss = boss.edges(">Z").chamfer(0.6)
    except Exception:
        pass
    return boss


def _strap_bracket(top_z):
    """A strap/loop bracket: a raised wall with a slot the strap threads through
    (interface = 'light'), or a flat tab (interface = 'phone_tab')."""
    if interface == "phone_tab":
        tab = (
            cq.Workplane("XY")
            .box(min(phone_w, 2.0 * BLOCK_R + 2.0 * EAR_LEN), 3.0, 22.0, centered=(True, True, False))
            .translate((0, 0, top_z))
        )
        try:
            tab = tab.edges("|Y and >Z").fillet(1.4)
        except Exception:
            pass
        return tab
    # 'light' / default: a loop wall with a strap slot.
    wall_h = 14.0
    loop = (
        cq.Workplane("XY")
        .box(2.0 * BLOCK_R, 4.0, wall_h, centered=(True, True, False))
        .translate((0, 0, top_z))
    )
    slot = (
        cq.Workplane("XY")
        .box(2.0 * BLOCK_R - 8.0, 6.0, 4.0, centered=(True, True, False))
        .translate((0, 0, top_z + wall_h - 5.0))
    )
    loop = loop.cut(slot)
    return loop


def _accessory(kind, top_z):
    if kind == "gopro":
        return _gopro_clevis(top_z)
    if kind == "1/4-20":
        return _quarter20_pad(top_z)
    return _strap_bracket(top_z)


# ── Part builders ────────────────────────────────────────────────────────────
def build_mount(iface):
    """Clamp base half + the chosen accessory on top + the cap half printed
    alongside so the whole clamp is one downloadable part."""
    base, top_z = build_clamp_base()
    base = base.union(_accessory(iface, top_z))
    cap = build_clamp_cap(clamp_w + 8.0)
    result_solid = base.union(cap)
    try:
        result_solid = result_solid.clean()
    except Exception:
        pass
    return result_solid


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "quarter20_mount":
    result = build_mount("1/4-20")
elif target_part == "strap_mount":
    result = build_mount(interface if interface in ("phone_tab", "light") else "light")
else:
    result = build_mount("gopro")
