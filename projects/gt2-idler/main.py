"""
GT2 Belt Idler Bracket — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Idlers and a tensioner bracket for GT2 2 mm synchronous belts (the belt on nearly
every desktop 3D printer, small CNC and plotter). The idler runs on a 608 bearing
(22 mm OD × 8 mm ID); the bracket bolts to the frame through slotted holes so the
belt tension can be dialled in. Two real interfaces meet here: the GT2 tooth
profile (shared with belt-clamp / timing-pulley) and the 608 press-fit seat
(shared with bearing-housing / linear-wheel).

GT2 reference:
  pitch      = 2.0 mm (tooth-to-tooth along the belt)
  tooth depth= 0.76 mm    pitch-line differential = 0.254 mm
  belt width = 6 or 9 mm (common)     idler bearing = 608 (8×22×7)
GT2 belts run on the SMOOTH BACK of a toothless idler; a toothed idler meshes the
teeth. A GT2 valley is approximated by a circular arc on the pitch circle — a
close, watertight stand-in (the same idiom the timing-pulley cartridge uses).

Modes (dispatched via `target_part`):
  * "smooth_idler"     — a toothless flanged idler on a 608; the belt back runs
                         on the smooth barrel.
  * "toothed_idler"    — a GT2-toothed idler that meshes the belt, on a 608.
  * "tensioner_bracket"— an L bracket carrying an idler stud, with SLOTTED frame
                         bolt holes (bolt_pattern) to set belt tension.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as BARE globals.
  - Read them via PARAM(lambda: <name>, <default>) — no globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq
import math


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── GT2 / HTD belt table ─────────────────────────────────────────────────────
BELT_TABLE = {
    "GT2-2mm": {"pitch": 2.0, "depth": 0.76, "pld": 0.254, "valley": 0.60},
    "GT2-3mm": {"pitch": 3.0, "depth": 1.14, "pld": 0.381, "valley": 0.90},
    "HTD-3M":  {"pitch": 3.0, "depth": 1.22, "pld": 0.381, "valley": 0.95},
}


def belt_spec(key):
    k = str(key).strip().upper().replace(" ", "")
    if k in ("GT2-2MM", "GT2", "2GT", "GT2-2"):
        return BELT_TABLE["GT2-2mm"]
    if k in ("GT2-3MM", "3GT", "GT2-3"):
        return BELT_TABLE["GT2-3mm"]
    if k in ("HTD-3M", "3M"):
        return BELT_TABLE["HTD-3M"]
    return BELT_TABLE["GT2-2mm"]


# 608 bearing (the idler's rolling element).
B_ID, B_OD, B_W = 8.0, 22.0, 7.0


# ── Parameters ───────────────────────────────────────────────────────────────
belt_type   = str(  PARAM(lambda: belt_type, "GT2-2mm"))   # GT2-2mm | GT2-3mm | HTD-3M
teeth       = int(  PARAM(lambda: teeth,          20))     # toothed-idler tooth count
belt_width  = float(PARAM(lambda: belt_width,      7.0))   # idler running width (mm)
od          = float(PARAM(lambda: od,             18.0))   # smooth-idler outside diameter (mm)
flange_h    = float(PARAM(lambda: flange_h,        2.0))   # flange rim over the belt line (mm)
arm_len     = float(PARAM(lambda: arm_len,        40.0))   # tensioner bracket arm length (mm)
slot_len    = float(PARAM(lambda: slot_len,       12.0))   # tension-adjust slot travel (mm)
bolt_dia    = float(PARAM(lambda: bolt_dia,        4.5))   # frame bolt clearance (M4≈4.5) (mm)

target_part = str(PARAM(lambda: target_part, "smooth_idler"))  # smooth_idler|toothed_idler|tensioner_bracket


# ── Derived / clamped geometry ───────────────────────────────────────────────
spec = belt_spec(belt_type)
pitch = spec["pitch"]
tooth_depth = spec["depth"]
pld = spec["pld"]
valley_r = spec["valley"]

teeth = max(10, min(teeth, 80))
belt_width = max(3.0, min(belt_width, 20.0))
width = max(B_W + 1.0, belt_width + 1.0)          # idler axial width ≥ bearing width
flange_h = max(0.0, min(flange_h, 8.0))
bolt_dia = max(2.0, min(bolt_dia, 10.0))
arm_len = max(24.0, min(arm_len, 120.0))
slot_len = max(bolt_dia + 4.0, min(slot_len, arm_len * 0.6))

# Toothed-idler pitch geometry (GT2 stand-in).
pitch_dia = teeth * pitch / math.pi
outside_dia = pitch_dia - 2.0 * pld
outside_r = outside_dia / 2.0
pitch_r = pitch_dia / 2.0
# Smooth idler OD clamped to clear the 608 seat.
od = max(B_OD + 4.0, min(od, 120.0))
seat_r = B_OD / 2.0
bore_r = B_ID / 2.0 + 0.3
stud_r = B_ID / 2.0 + 0.3                          # idler stud on the bracket


# ── Helpers ──────────────────────────────────────────────────────────────────
def _seat_608(body, running_r, w):
    """Bore the axle through, and — only when the rim is large enough to contain
    the 22 mm bearing OD with a wall — cut the 608 press-fit seat from the top
    face (leaving a central shoulder). The bore diameter is clamped to leave a
    real wall inside the running surface, so the part is honest at every size:
      * large rim (> 608 + wall) → full 608 press-fit seat + 8 mm shaft bore;
      * medium rim               → 8 mm shaft bore (a shaft-mount idler);
      * tiny rim (e.g. 20-tooth GT2, ~12 mm OD) → a proportionally smaller shaft
        bore that still leaves a wall (a small GT2 shaft pulley).
    A GT2 idler only carries a 608 once it is physically big enough to."""
    # Largest bore that still leaves ≥1.6 mm wall inside the running surface.
    max_bore_r = max(1.2, running_r - 1.6)
    ax_r = min(bore_r, max_bore_r)
    axle = cq.Workplane("XY").circle(ax_r).extrude(w + 2.0).translate((0, 0, -1.0))
    body = body.cut(axle)
    if running_r > seat_r + 2.0:
        seat = (
            cq.Workplane("XY")
            .circle(seat_r)
            .extrude(-(B_W + 0.01))
            .translate((0, 0, w + 0.005))
        )
        body = body.cut(seat)
    return body


def _flanges(body, running_r, w):
    if flange_h <= 0.05:
        return body
    fr = running_r + flange_h
    bot = cq.Workplane("XY").circle(fr).extrude(1.6)
    top = cq.Workplane("XY").circle(fr).extrude(1.6).translate((0, 0, w - 1.6))
    return body.union(bot).union(top)


def _toothed_rim(w):
    """A cylinder of the pulley OD with `teeth` valley arcs cut into the rim —
    each valley a vertical cylinder on the pitch circle. Combined cutter, one
    subtraction (watertight GT2 stand-in)."""
    rim = cq.Workplane("XY").circle(outside_r).extrude(w)
    cutter = None
    for i in range(teeth):
        ang = 2.0 * math.pi * i / teeth
        cx = pitch_r * math.cos(ang)
        cy = pitch_r * math.sin(ang)
        pin = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(cx, cy, -0.5))
            .circle(valley_r)
            .extrude(w + 1.0)
        )
        cutter = pin if cutter is None else cutter.union(pin)
    if cutter is not None:
        rim = rim.cut(cutter)
    return rim


# ── Builders ─────────────────────────────────────────────────────────────────
def build_smooth_idler():
    """Toothless flanged idler barrel on a 608 seat."""
    body = cq.Workplane("XY").circle(od / 2.0).extrude(width)
    body = _flanges(body, od / 2.0, width)
    body = _seat_608(body, od / 2.0, width)
    return body


def build_toothed_idler():
    """GT2-toothed idler on a 608 seat, with retaining flanges."""
    body = _toothed_rim(width)
    body = _flanges(body, outside_r, width)
    body = _seat_608(body, outside_r, width)
    return body


def build_tensioner_bracket():
    """An L bracket: a base foot that bolts to the frame through two SLOTTED
    holes (so it can slide to tension the belt) and an upstanding stud boss that
    carries the idler's 608 on a printed 8 mm stud."""
    t = max(4.0, bolt_dia * 0.9)
    base_w = max(2.0 * seat_r + 6.0, bolt_dia * 4.0)
    # Base foot.
    base = cq.Workplane("XY").box(arm_len, base_w, t, centered=(False, True, False))
    # Upstand at the far end carrying the idler.
    boss_h = width + 4.0
    upstand = (
        cq.Workplane("XY")
        .box(t, base_w, boss_h, centered=(False, True, False))
        .translate((arm_len - t, 0, 0))
    )
    body = base.union(upstand)
    # Gusset web tying upstand to base.
    web = (
        cq.Workplane("XZ")
        .workplane(offset=base_w / 2.0)
        .polyline([(arm_len - t, t), (arm_len - t, boss_h * 0.7),
                   (arm_len - t - boss_h * 0.6, t)])
        .close()
        .extrude(-base_w)
    )
    body = body.union(web)

    # Idler stud: a horizontal 8 mm post on the upstand (belt idler presses on it).
    stud = (
        cq.Workplane("YZ")
        .workplane(offset=arm_len - t)
        .circle(stud_r)
        .extrude(width + 1.0)
        .translate((0, 0, boss_h - width / 2.0 - 1.0))
    )
    body = body.union(stud)

    # Two SLOTTED frame bolt holes in the base (tension adjustment) — obround via
    # native slot2D so the mesh stays watertight at any slot length.
    slot_off = base_w / 2.0 - (bolt_dia + 2.0)
    for sy in (-slot_off, slot_off):
        slot = (
            cq.Workplane("XY")
            .slot2D(max(bolt_dia + 0.01, slot_len), bolt_dia, angle=0)
            .extrude(t + 2.0)
            .translate((arm_len * 0.35, sy, -1.0))
        )
        body = body.cut(slot)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "toothed_idler":
    result = build_toothed_idler()
elif target_part == "tensioner_bracket":
    result = build_tensioner_bracket()
else:
    result = build_smooth_idler()
