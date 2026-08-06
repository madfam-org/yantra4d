"""
LED Strip Channel — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A mounting channel and diffuser for adhesive LED strip (5050 / 2835 tape). The
U-channel holds the strip, protects it, and gives it a surface to sit proud of;
a snap-on cover clips into the channel lips to diffuse the LEDs; a corner piece
turns a run through 90°. Sized by the strip width so common tapes drop straight
in.

Modes are dispatched via `target_part`:
  * "channel"        — the U-channel body (strip bed + snap lips + screw pilots).
  * "diffuser_cover" — the snap-in cover strip that clips into the channel lips.
  * "corner"         — a 90° channel elbow to route a run around a corner.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `strip_width`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval.
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
strip_width = float(PARAM(lambda: strip_width, 10.0))   # LED tape width (5050 ≈ 10 mm)
length      = float(PARAM(lambda: length,     150.0))   # channel length (straight run)
wall        = float(PARAM(lambda: wall,         1.6))   # channel wall thickness
floor       = float(PARAM(lambda: floor,        1.4))   # channel floor thickness
depth       = float(PARAM(lambda: depth,        7.0))   # interior depth (LED + wiring)
lip         = float(PARAM(lambda: lip,          1.0))   # inward snap-lip that holds the cover
screw_pilots = bool(PARAM(lambda: screw_pilots, True))  # mounting screw pilots in the floor

target_part = str(PARAM(lambda: target_part, "channel"))

# ── Derived ──────────────────────────────────────────────────────────────────
strip_width = max(4.0, min(strip_width, 20.0))
length = max(20.0, min(length, 400.0))
wall = max(1.0, min(wall, 4.0))
floor = max(1.0, min(floor, 4.0))
depth = max(3.0, min(depth, 20.0))
lip = max(0.4, min(lip, wall))

clearance = 0.4                          # per-side gap so the strip drops in
inner_w = strip_width + 2.0 * clearance  # channel interior width
outer_w = inner_w + 2.0 * wall           # channel exterior width
outer_h = floor + depth                  # channel exterior height


# ── Helpers ──────────────────────────────────────────────────────────────────
def _channel(run_len):
    """The U-channel as a solid box minus the interior cavity, with two top lips
    left standing (a mouth narrower than the cavity)."""
    body = cq.Workplane("XY").box(outer_w, run_len, outer_h, centered=(True, True, False))

    # Interior cavity (strip bed), open at the top.
    cavity = (
        cq.Workplane("XY").workplane(offset=floor)
        .box(inner_w, run_len + 2.0, depth + 1.0, centered=(True, True, False))
    )
    body = body.cut(cavity)

    # Snap lips: re-add two thin ledges at the top inner edges that overhang the
    # cavity (the cover clips under them). Add them back as solid, then the mouth
    # between them stays open.
    lip_z = outer_h - lip
    for sx in (-1.0, 1.0):
        x = sx * (inner_w / 2.0 - lip / 2.0)
        ledge = (
            cq.Workplane("XY").workplane(offset=lip_z)
            .transformed(offset=cq.Vector(x, 0, 0))
            .box(lip, run_len, lip, centered=(True, True, False))
        )
        body = body.union(ledge)
    return body


def build_channel():
    body = _channel(length)
    if screw_pilots:
        n = max(2, int(length // 60.0))
        ys = [-length / 2.0 + length * i / (n - 1) for i in range(n)]
        pilots = (
            cq.Workplane("XY").workplane(offset=-0.5)
            .pushPoints([(0.0, y) for y in ys]).circle(1.6).extrude(floor + 1.0)
        )
        # countersink cups on the strip bed
        cups = (
            cq.Workplane("XY").workplane(offset=floor)
            .pushPoints([(0.0, y) for y in ys]).circle(3.0).extrude(-min(floor - 0.4, 1.0))
        )
        body = body.cut(pilots).cut(cups)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_diffuser_cover():
    """A cover strip that snaps into the channel lips: a top plate with two
    barbed legs whose outer tips tuck under the channel's inward lips."""
    cover_w = inner_w - 0.3               # sits between the channel walls
    plate_t = max(1.2, wall)
    leg_h = lip + 1.2
    body = cq.Workplane("XY").box(cover_w, length, plate_t, centered=(True, True, False))

    # Two legs hanging down with an outward barb at the tip.
    for sx in (-1.0, 1.0):
        x = sx * (cover_w / 2.0 - 0.6)
        leg = (
            cq.Workplane("XY").transformed(offset=cq.Vector(x, 0, -leg_h))
            .box(1.2, length, leg_h, centered=(True, True, False))
        )
        barb = (
            cq.Workplane("XY").transformed(offset=cq.Vector(x + sx * 0.6, 0, -leg_h))
            .box(1.2, length, lip, centered=(True, True, False))
        )
        body = body.union(leg).union(barb)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_corner():
    """A 90° elbow: two short channel legs meeting at a mitre so a run turns a
    corner. Built as two channel prisms (one along Y, one along X) unioned; each
    leg is `arm` long from the inside corner."""
    arm = max(30.0, outer_w * 2.5)

    # Leg A along +Y, shifted so it starts at the corner origin.
    leg_a = _channel(arm).translate((0, arm / 2.0, 0))
    # Leg B along +X: build a Y-channel then rotate 90° about Z.
    leg_b = _channel(arm).rotate((0, 0, 0), (0, 0, 1), 90).translate((arm / 2.0, 0, 0))

    body = leg_a.union(leg_b)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
_dispatch = {
    "channel": build_channel,
    "diffuser_cover": build_diffuser_cover,
    "corner": build_corner,
}

result = _dispatch.get(target_part, build_channel)()
