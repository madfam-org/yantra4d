"""
Box-Joint Indexing Jig — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A jig that indexes evenly spaced fingers for box (finger) joints on a router
table or table saw. The registration key is exactly one finger wide and sits one
finger-width from the cut, so each pass drops onto the previous notch and steps
the workpiece over by a perfect pitch.

Three modes, dispatched by `target_part`:
  - index_key  : a single comb of fingers — the master index key of `finger_w`
                 pitch that defines the joint spacing.
  - fence_jig  : a backer fence with a protruding index pin one finger-width from
                 a bit clearance slot, for mounting to a miter gauge / sled.
  - adjustable : a fence with a slotted key carrier so the index pin position is
                 tunable via a fixing bolt for fine pitch adjustment.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `finger_w`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval/
    getattr — they are not in the sandbox's allowed builtins.
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
finger_w    = float(PARAM(lambda: finger_w,    6.0))   # finger width == joint pitch
mat_thick   = float(PARAM(lambda: mat_thick,  12.0))   # stock thickness (finger depth)
fence_len   = float(PARAM(lambda: fence_len, 160.0))   # backer fence length
fence_h     = float(PARAM(lambda: fence_h,    50.0))   # fence height
base_t      = float(PARAM(lambda: base_t,     10.0))   # jig base thickness
n_fingers   = int(  PARAM(lambda: n_fingers,    7))    # fingers on the index key
bolt_bore   = float(PARAM(lambda: bolt_bore,   5.5))   # fixing-bolt bore (adjustable)
slot_len    = float(PARAM(lambda: slot_len,   30.0))   # adjustment slot length

target_part = str(PARAM(lambda: target_part, "index_key"))

# A finger joint alternates finger / gap of equal width; depth = stock thickness.
depth = mat_thick


# ── Helpers ──────────────────────────────────────────────────────────────────
def prism(w, d, h, cx=True, cy=True):
    return cq.Workplane("XY").box(w, d, h, centered=(cx, cy, False))


def bore_y(dia, length, at):
    """Horizontal (Y-axis) bore through a fence, positioned at (x, z)."""
    return (
        cq.Workplane("XZ")
        .circle(dia / 2.0)
        .extrude(length + 2.0)
        .translate((at[0], 1.0, at[1]))
    )


# ── Index key (master finger comb) ───────────────────────────────────────────
def build_index_key():
    """A comb of `n_fingers` fingers at `finger_w` pitch, `depth` tall, on a base
    rail. This is the reference that sets the joint geometry."""
    n = max(2, n_fingers)
    span = (2 * n - 1) * finger_w          # fingers + equal gaps
    w = span
    d = max(finger_w * 3.0, 18.0)
    base = prism(w, d, base_t, cx=True, cy=True)

    fingers = None
    for i in range(n):
        x = -span / 2.0 + finger_w / 2.0 + i * 2.0 * finger_w
        f = prism(finger_w, d, depth, cx=True, cy=True).translate((x, 0, base_t))
        fingers = f if fingers is None else fingers.union(f)
    body = base.union(fingers)
    try:
        body = body.edges(">Z and |Y").chamfer(min(finger_w * 0.15, 0.8))
    except Exception:
        pass
    return body


# ── Fence jig (backer fence + fixed index pin) ───────────────────────────────
def build_fence_jig():
    """A tall backer fence with a bit-clearance slot and one index pin standing
    exactly one finger-width to the side of the slot."""
    base = prism(fence_len, base_t + finger_w, base_t, cx=True, cy=True)
    fence = prism(fence_len, base_t, fence_h, cx=True, cy=True).translate(
        (0, base_t / 2.0 + finger_w / 2.0, base_t)
    )
    body = base.union(fence)

    # Bit clearance slot through the fence base, at centre.
    slot = prism(finger_w, base_t + finger_w + 2.0, depth + 2.0, cx=True, cy=True).translate(
        (0, 0, base_t - depth)
    )
    body = body.cut(slot)

    # Index pin: one finger to the +X side, standing proud of the base.
    pin = prism(finger_w, base_t + finger_w, depth, cx=True, cy=True).translate(
        (2.0 * finger_w, 0, base_t)
    )
    body = body.union(pin)
    try:
        body = body.edges("|Z").fillet(min(finger_w * 0.1, 0.6))
    except Exception:
        pass
    return body


# ── Adjustable (slotted key carrier) ─────────────────────────────────────────
def build_adjustable():
    """A fence whose index pin rides a slotted carrier; a fixing bolt through the
    adjustment slot locks the pin at a tuned distance from the bit slot."""
    base = prism(fence_len, base_t + 2.0 * finger_w, base_t, cx=True, cy=True)
    fence = prism(fence_len, base_t, fence_h, cx=True, cy=True).translate(
        (0, base_t / 2.0 + finger_w, base_t)
    )
    body = base.union(fence)

    # Bit clearance slot at centre.
    slot = prism(finger_w, base_t + 2.0 * finger_w + 2.0, depth + 2.0, cx=True, cy=True).translate(
        (0, 0, base_t - depth)
    )
    body = body.cut(slot)

    # Adjustment slot (elongated) through the fence for the fixing bolt.
    adj = (
        cq.Workplane("XZ")
        .slot2D(max(slot_len, bolt_bore * 2.0), bolt_bore, 0)
        .extrude(base_t + 2.0)
        .translate((2.0 * finger_w, base_t + 2.0 * finger_w, base_t + fence_h * 0.5))
    )
    body = body.cut(adj)

    # A carrier boss around the slot to seat a washer/nut.
    boss = prism(bolt_bore * 3.0, base_t + 2.0 * finger_w, 3.0, cx=True, cy=True).translate(
        (2.0 * finger_w, 0, base_t + fence_h)
    )
    body = body.union(boss)
    body = body.cut(bore_y(bolt_bore, base_t + 2.0 * finger_w, (2.0 * finger_w, base_t + fence_h + 1.5)))
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "fence_jig":
    result = build_fence_jig()
elif target_part == "adjustable":
    result = build_adjustable()
else:
    result = build_index_key()
