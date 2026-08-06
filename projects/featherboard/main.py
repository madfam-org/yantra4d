"""
Featherboard — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

An anti-kickback featherboard: a bank of angled, flexible fingers that press a
workpiece against a fence or table and act as a one-way ratchet — the workpiece
feeds forward freely but is gripped if it tries to kick back. The mount varies
by machine: a miter-slot bar, a T-slot / track runner, or a clamp-on body.

Three modes, dispatched by `target_part`:
  - tslot_feather : body with a T-track runner slot for a T-slot fence / table.
  - miter_feather : body with a 3/4in x 3/8in miter-slot bar underneath.
  - clamp_feather : plain body with clamp-through slots to fix to any surface.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `feather_n`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval/
    getattr — they are not in the sandbox's allowed builtins.
  - Assign the final solid to a top-level name `result`.
"""

import math

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
feather_n   = int(  PARAM(lambda: feather_n,    12))    # number of fingers
kerf        = float(PARAM(lambda: kerf,        1.6))    # slot between fingers (flex gap)
finger_ang  = float(PARAM(lambda: finger_ang, 30.0))    # finger rake angle (deg)
body_w      = float(PARAM(lambda: body_w,     90.0))    # feather bank width
body_len    = float(PARAM(lambda: body_len,   70.0))    # body length (mount direction)
thick       = float(PARAM(lambda: thick,       9.0))    # board thickness
finger_len  = float(PARAM(lambda: finger_len, 35.0))    # length of the flexing fingers

target_part = str(PARAM(lambda: target_part, "tslot_feather"))

# Miter bar nominal: 3/4 in wide x 3/8 in deep runner.
MITER_W = 19.05
MITER_D = 9.53
# T-track runner nominal (common 3/4in T-track): 19 mm wide slot lip.
TTRACK_W = 19.0
TTRACK_D = 6.0


# ── Helpers ──────────────────────────────────────────────────────────────────
def prism(w, d, h, cx=True, cy=True):
    return cq.Workplane("XY").box(w, d, h, centered=(cx, cy, False))


def build_feather_bank():
    """A solid body with a comb of angled fingers cut into the leading edge.
    Fingers are formed by cutting `feather_n - 1` raked kerf slots into a solid
    bank, leaving flexible teeth. Returns (body) as a watertight solid."""
    # Solid slab: body region + finger region ahead of it.
    total_len = body_len + finger_len
    body = prism(body_w, total_len, thick, cx=True, cy=True)

    # Angled kerf slots cut into the +Y (leading) finger region only.
    n = max(2, feather_n)
    pitch = body_w / n
    slot_len = finger_len + 4.0
    y0 = total_len / 2.0 - finger_len / 2.0 + 2.0  # centre of finger region
    dx = math.tan(math.radians(max(0.0, min(finger_ang, 55.0))))  # rake shift factor
    for i in range(1, n):
        x = -body_w / 2.0 + i * pitch
        slot = (
            cq.Workplane("XY")
            .box(kerf, slot_len, thick + 2.0, centered=(True, True, False))
            .rotate((0, 0, 0), (0, 0, 1), -math.degrees(math.atan(dx)))
            .translate((x, y0, -1.0))
        )
        body = body.cut(slot)

    # Trim the finger tips to a clean angled leading edge (rake the whole bank).
    tip_trim = (
        cq.Workplane("XY")
        .box(body_w + 4.0, finger_len, thick + 2.0, centered=(True, True, False))
        .rotate((0, 0, 0), (1, 0, 0), 0.0)
        .translate((0, total_len / 2.0 + finger_len * 0.5 - 1.0, -1.0))
    )
    # Only trim the excess beyond the intended finger length.
    body = body.cut(tip_trim.translate((0, finger_len * 0.5 + 1.0, 0)))
    return body, total_len


# ── T-slot featherboard ──────────────────────────────────────────────────────
def build_tslot_feather():
    body, total_len = build_feather_bank()
    # Two through-slots along the mount (trailing) region for T-track knobs.
    for sx in (-1, 1):
        slot = (
            cq.Workplane("XZ")
            .slot2D(max(TTRACK_W * 1.6, 26.0), 7.0, 0)
            .extrude(total_len + 2.0)
            .translate((sx * body_w * 0.28, total_len / 2.0 - 1.0, thick / 2.0))
        )
        body = body.cut(slot)
    # Runner rib underneath that seats in a T-track.
    rib = prism(TTRACK_W, body_len * 0.7, TTRACK_D, cx=True, cy=True).translate(
        (0, -total_len / 2.0 + body_len * 0.4, -TTRACK_D)
    )
    body = body.union(rib)
    return body


# ── Miter-slot featherboard ──────────────────────────────────────────────────
def build_miter_feather():
    body, total_len = build_feather_bank()
    # 3/4in x 3/8in miter bar underneath, running in the mount direction (Y).
    bar = prism(MITER_W, body_len * 0.9, MITER_D, cx=True, cy=True).translate(
        (0, -total_len / 2.0 + body_len * 0.45, -MITER_D)
    )
    body = body.union(bar)
    # A knob slot to lock the bar's cam (single central slot).
    slot = (
        cq.Workplane("XZ")
        .slot2D(30.0, 7.0, 0)
        .extrude(total_len + 2.0)
        .translate((0, total_len / 2.0 - 1.0, thick / 2.0))
    )
    body = body.cut(slot)
    return body


# ── Clamp-on featherboard ────────────────────────────────────────────────────
def build_clamp_feather():
    body, total_len = build_feather_bank()
    # Two open-ended clamp slots so a clamp or bolt fixes it to any surface.
    for sx in (-1, 1):
        slot = (
            cq.Workplane("XZ")
            .slot2D(38.0, 8.0, 0)
            .extrude(total_len + 2.0)
            .translate((sx * body_w * 0.30, total_len / 2.0 - 1.0, thick / 2.0))
        )
        body = body.cut(slot)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "miter_feather":
    result = build_miter_feather()
elif target_part == "clamp_feather":
    result = build_clamp_feather()
else:
    result = build_tslot_feather()
