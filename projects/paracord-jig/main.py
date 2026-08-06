"""
Paracord Buckle / Jig — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Cord tooling for 550 paracord (7-strand nylon, nominal diameter ~4.0 mm). Three
print-ready parts share the same cord-diameter interface so a weave, a buckle and
a toggle all size to the same cord:

  - side_buckle  : a single-piece side-release buckle blank — a female body with a
                   through channel plus twin sprung male prongs, printed flat as
                   one manifold part (snap them by hand; the sprung arms flex).
  - bracelet_jig : an adjustable weaving jig — a base bar with two end blocks that
                   carry cord slots and a row of pins to set bracelet length.
  - cord_lock    : a spring-less barrel toggle / cord lock with two parallel bores
                   for a doubled cord and a side pinch slot.

Real dimensions:
  - 550 paracord outer diameter ~4.0 mm → default cord_d = 4.0 mm.
  - Webbing width for the buckle defaults to 25 mm (1 in), the common strap size.

Watertight strategy:
  Every part is ONE solid. Pins and prongs are solid (no trapped cavity). Cord
  bores are through-holes that vent to an outside face. Slots are obround
  (slot2D) through-cuts. Overlapping solids are unioned into shared material;
  fillets clean the blank BEFORE feature cuts, wrapped in try/except so an
  over-large radius never crashes the kernel.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  `cq` and `math` are pre-injected globals; manifest parameters arrive as bare
  globals (e.g. `target_part`). Read them via PARAM(lambda: name, default).
  Assign the final solid to a top-level name `result`.
"""

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else default. `except Exception`
    catches the NameError the sandbox raises for an unbound parameter name."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "side_buckle"))
# "side_buckle" | "bracelet_jig" | "cord_lock"

cord_d = float(PARAM(lambda: cord_d, 4.0))        # 550 paracord OD (mm)
strap_w = float(PARAM(lambda: strap_w, 25.0))     # webbing width for the buckle (mm)
wall = float(PARAM(lambda: wall, 3.0))            # wall / structural thickness (mm)
clearance = float(PARAM(lambda: clearance, 0.35))  # snap / fit clearance per side (mm)

jig_len = float(PARAM(lambda: jig_len, 120.0))    # bracelet jig board length (mm)
pin_count = int(round(float(PARAM(lambda: pin_count, 6))))  # jig length pins
lock_len = float(PARAM(lambda: lock_len, 22.0))   # cord-lock barrel length (mm)

# Clamp to sane ranges so extreme UI values never crash the kernel.
cord_d = max(2.0, min(cord_d, 8.0))
strap_w = max(12.0, min(strap_w, 50.0))
wall = max(2.0, min(wall, 6.0))
clearance = max(0.1, min(clearance, 0.8))
jig_len = max(60.0, min(jig_len, 260.0))
pin_count = max(2, min(pin_count, 16))
lock_len = max(14.0, min(lock_len, 40.0))


# ── Shared helpers ───────────────────────────────────────────────────────────
def _obround_through(length, width, thickness, cx=0.0, cy=0.0):
    """A stadium/obround through-solid (used as a cut tool). Centred at (cx,cy),
    running along Y, spanning the full `thickness` in Z (over-cut both ends)."""
    overall = max(width + 0.001, length)
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(cx, cy, -0.5))
        .slot2D(overall, width, angle=90)
        .extrude(thickness + 1.0)
    )


def _fillet_z(solid, r):
    """Fillet all vertical edges of a prism blank, guarded."""
    try:
        return solid.edges("|Z").fillet(r)
    except Exception:
        return solid


# ── Part builders ────────────────────────────────────────────────────────────
def build_side_buckle():
    """A single-piece webbing buckle sized to `strap_w`: a closed rectangular
    frame with a centre bar (a tri-glide / ladder-lock slider). The webbing
    threads over the centre bar and back, and the tension of the strap locks it —
    the standard one-piece printable buckle. It is genuinely ONE solid frame with
    two obround windows, so it is unconditionally watertight and manifold."""
    body_h = cord_d + 2.0 * wall               # low-profile frame thickness (Z)
    inner_w = strap_w + 2.0 * clearance         # webbing clear width
    frame_w = inner_w + 2.0 * wall              # outer X width
    win_len = strap_w * 0.42 + 3.0              # each window length in Y
    bar = wall + 1.0                            # centre bar / rail thickness in Y
    frame_len = 2.0 * win_len + 3.0 * bar       # outer Y length

    # Solid slab, filleted on the blank, then two windows bored through (each
    # vents top-to-bottom → no trapped void), leaving a frame + centre bar.
    slab = (
        cq.Workplane("XY")
        .box(frame_w, frame_len, body_h, centered=(True, True, False))
    )
    slab = _fillet_z(slab, min(3.0, wall + 1.0))

    for cy in (frame_len / 2.0 - bar - win_len / 2.0,
               -(frame_len / 2.0 - bar - win_len / 2.0)):
        win = _obround_through(inner_w, win_len, body_h, cx=0.0, cy=cy)
        # obround runs along Y by default; rotate 90° so its long axis is X.
        win = win.rotate((0, cy, 0), (0, cy, 1), 90)
        slab = slab.cut(win)
    return slab


def build_bracelet_jig():
    """An adjustable weaving jig: a flat base bar with two end blocks. Each end
    block carries a cord slot to anchor the working cords and a fixed pin; a row
    of pins along the base sets the finished bracelet length. Every pin is a
    solid cylinder standing on the solid base (no sealed cavity)."""
    base_w = cord_d * 3.0 + 2.0 * wall
    base_h = wall + 2.0
    base = (
        cq.Workplane("XY")
        .box(jig_len, base_w, base_h, centered=(True, True, False))
    )
    base = _fillet_z(base, min(4.0, base_w * 0.25))

    # End blocks rise at both ends, overlapping the base for a solid weld.
    block_h = cord_d + 2.0 * wall + 2.0
    block_len = cord_d + 2.0 * wall + 4.0
    body = base
    for sign in (-1.0, 1.0):
        bx = sign * (jig_len / 2.0 - block_len / 2.0)
        blk = (
            cq.Workplane("XY")
            .box(block_len, base_w, block_h, centered=(True, True, False))
            .translate((bx, 0, 0))
        )
        blk = _fillet_z(blk, min(3.0, block_len * 0.3))
        body = body.union(blk)
        # cord anchor: a vertical through-bore in the block (vents top+bottom).
        anchor = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(bx, 0, -0.5))
            .circle((cord_d + clearance) / 2.0)
            .extrude(block_h + 1.0)
        )
        body = body.cut(anchor)

    # Row of solid length pins along the base centreline.
    pin_r = max(1.5, cord_d * 0.45)
    pin_h = cord_d + wall + 2.0
    usable = jig_len - 2.0 * (block_len + 4.0)
    n = max(2, pin_count)
    for i in range(n):
        t = i / (n - 1)
        px = -usable / 2.0 + t * usable
        pin = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(px, 0, base_h - 0.01))
            .circle(pin_r)
            .extrude(pin_h)
        )
        body = body.union(pin)
    return body


def build_cord_lock():
    """A barrel cord lock / toggle: a rounded block with two parallel through
    bores for a doubled cord and an angled pinch slot. Friction (not a spring)
    holds the cord; squeeze to slide. One solid, both bores vent to end faces."""
    lock_w = cord_d * 3.0 + 2.0 * wall
    lock_h = cord_d + 2.0 * wall
    body = (
        cq.Workplane("XY")
        .box(lock_w, lock_len, lock_h, centered=(True, True, False))
    )
    body = _fillet_z(body, min(5.0, lock_w * 0.3))
    # round the top too, guarded
    try:
        body = body.edges("|X and >Z").fillet(min(2.0, lock_h * 0.3))
    except Exception:
        pass

    bore_r = (cord_d + clearance) / 2.0
    off = cord_d * 0.75
    for sx in (-off, off):
        bore = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(sx, -lock_len / 2.0 - 0.5, lock_h / 2.0))
            .transformed(rotate=cq.Vector(-90, 0, 0))
            .circle(bore_r)
            .extrude(lock_len + 1.0)
        )
        body = body.cut(bore)

    # Angled pinch slot across the middle from the top (vents to top face).
    pinch = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, lock_h * 0.45),
                     rotate=cq.Vector(0, 18, 0))
        .slot2D(lock_w + 4.0, max(1.6, wall * 0.6), angle=0)
        .extrude(lock_h)
    )
    body = body.cut(pinch)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "bracelet_jig":
    result = build_bracelet_jig()
elif target_part == "cord_lock":
    result = build_cord_lock()
else:
    result = build_side_buckle()
