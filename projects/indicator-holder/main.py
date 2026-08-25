"""
Dial Indicator Holder — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

An articulated holder for a dial or test indicator that grips the industry
standard 8 mm indicator stem (Mitutoyo Series 2 / AGD Group 2 and equivalents;
also 3/8 in = 9.525 mm). Print a stem clamp (the business end), a snug reach arm
(stem clamp on one end, post clamp on the other), and a base with a vertical
post — together a rigid stand that puts a gauge exactly where the measurement is.

Shares the 8 mm indicator-stem socket with the `indicator-base` cartridge, so a
gauge fits either holder.

Real dimensions (dial-indicator convention):
  - indicator stem = 8.0 mm nominal (bore cut at +0.1 mm clearance)
  - stem_dia range reaches 9.525 mm (3/8 in) for imperial-stem indicators
  - the clamp is a saw-cut split ring closed by a cross screw — print stiffness
    does the gripping.

Watertight strategy:
  Clamp bodies are boxes with a horizontal cross-BORE (through-hole, vented at
  both ends) closed by a thin saw SLIT (through-cut to the bore) and a cross
  SCREW hole (through). The arm is a solid bar unioned into both clamp bosses
  with overlap (no tangent joins). The post is a solid cylinder unioned into a
  filleted base blank. Fillets on clean blanks BEFORE cuts, wrapped in
  try/except.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected; params arrive as BARE globals.
  - Read every param via PARAM(lambda: <name>, <default>).
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters (8 mm indicator stem) ─────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "stem_clamp"))
# "stem_clamp" | "snug_arm" | "base_post"

stem_dia = float(PARAM(lambda: stem_dia, 8.0))        # indicator stem diameter, mm
post_dia = float(PARAM(lambda: post_dia, 12.0))       # vertical post diameter, mm
arm_len = float(PARAM(lambda: arm_len, 70.0))         # reach arm length (centre-centre)
wall = float(PARAM(lambda: wall, 5.0))                # clamp / body wall thickness
clamp_screw_d = float(PARAM(lambda: clamp_screw_d, 3.4))  # clamp screw clearance (M3)
post_height = float(PARAM(lambda: post_height, 90.0))  # base post height, mm
base_width = float(PARAM(lambda: base_width, 60.0))   # base plate width, mm

# Clamp to sane ranges so extreme UI values never crash the kernel.
stem_dia = max(6.0, min(stem_dia, 10.0))
post_dia = max(8.0, min(post_dia, 20.0))
arm_len = max(30.0, min(arm_len, 140.0))
wall = max(3.0, min(wall, 10.0))
clamp_screw_d = max(2.2, min(clamp_screw_d, 6.0))
post_height = max(40.0, min(post_height, 160.0))
base_width = max(40.0, min(base_width, 110.0))

_stem_bore = stem_dia + 0.1        # +0.1 mm reaming clearance (metrology convention)
_post_bore = post_dia + 0.25       # slip-fit over the post


# ── Split-clamp boss (the reusable metrology idiom) ──────────────────────────
def _clamp_boss(bore_d, along="X"):
    """A rectangular boss with a horizontal cross-bore (through, vented both
    ends), a saw slit opening the bore to one face, and a cross clamp screw.
    Centred on the origin; bore axis runs along `along` ('X' or 'Y'). Returns
    (solid, boss_w_across, boss_h)."""
    boss_across = bore_d + 2.0 * wall        # width perpendicular to the bore axis
    boss_h = bore_d + 2.0 * wall             # height (Z)
    boss_along = bore_d + 2.0 * wall         # length along the bore axis

    if along == "X":
        bx, by = boss_along, boss_across
        bore_plane = "YZ"
    else:
        bx, by = boss_across, boss_along
        bore_plane = "XZ"

    boss = (
        cq.Workplane("XY")
        .box(bx, by, boss_h, centered=(True, True, False))
    )
    try:
        boss = boss.edges("|Z").fillet(min(2.5, wall - 0.5))
    except Exception:
        pass

    # Cross-bore through the boss, centred at mid-height.
    bore = (
        cq.Workplane(bore_plane)
        .transformed(offset=cq.Vector(0, boss_h / 2.0, 0))
        .circle(bore_d / 2.0)
        .extrude(max(bx, by) / 2.0 + 2.0, both=True)
    )
    boss = boss.cut(bore)

    # Saw slit: a thin slot from the +Y (or +X) outer face down to just past the
    # bore centre, full height, so the ring can pinch shut. Opens the bore to a
    # face (vents; not a trapped void).
    if along == "X":
        slit = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, by / 2.0 * 0.5, boss_h / 2.0))
            .box(1.6, by, boss_h + 2.0, centered=(True, True, True))
        )
    else:
        slit = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(bx / 2.0 * 0.5, 0, boss_h / 2.0))
            .box(bx, 1.6, boss_h + 2.0, centered=(True, True, True))
        )
    boss = boss.cut(slit)

    # Cross clamp screw: perpendicular to both bore and slit, through the split
    # so tightening closes the slit. Runs along the slit-normal, above the bore.
    scr_z = boss_h / 2.0
    if along == "X":
        # slit is in the XZ mid-plane opening +Y; screw runs along Y through it.
        screw = (
            cq.Workplane("XZ")
            .transformed(offset=cq.Vector(0, scr_z, 0))
            .circle(max(0.6, clamp_screw_d / 2.0))
            .extrude(by / 2.0 + 2.0, both=True)
        )
    else:
        screw = (
            cq.Workplane("YZ")
            .transformed(offset=cq.Vector(0, scr_z, 0))
            .circle(max(0.6, clamp_screw_d / 2.0))
            .extrude(bx / 2.0 + 2.0, both=True)
        )
    boss = boss.cut(screw)
    return boss, boss_across, boss_h


# ── Part builders ────────────────────────────────────────────────────────────
def build_stem_clamp():
    """The business end: a split clamp gripping the 8 mm indicator stem, on a
    short flat tab with a mount bolt hole so it fastens to an arm or a magnetic
    base directly."""
    boss, across, boss_h = _clamp_boss(_stem_bore, along="X")

    # A mounting tab off the -Y side, in the same block, with a through bolt hole.
    tab_len = across
    tab = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -(across / 2.0 + tab_len / 2.0 - wall), 0))
        .box(across, tab_len, wall * 1.4, centered=(True, True, False))
    )
    body = boss.union(tab)
    hole = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -(across / 2.0 + tab_len / 2.0 - wall), -0.5))
        .circle(max(0.6, clamp_screw_d / 2.0 + 0.4))
        .extrude(wall * 1.4 + 1.0)
    )
    body = body.cut(hole)
    return body


def build_snug_arm():
    """A reach arm: a stem clamp at +Y end and a post clamp at -Y end, joined by
    a solid bar. Grip the indicator stem at one end, clamp onto the vertical
    post at the other, and swing the gauge out over the work."""
    stem_boss, s_across, s_h = _clamp_boss(_stem_bore, along="X")
    post_boss, p_across, p_h = _clamp_boss(_post_bore, along="Z")

    half = arm_len / 2.0
    stem_boss = stem_boss.translate((0, half, 0))
    post_boss = post_boss.translate((0, -half, 0))

    # Solid connecting bar overlapping into both bosses (union of overlapping
    # solids, not tangent). Bar height = min boss height so it blends flush.
    bar_h = min(s_h, p_h)
    bar_w = min(s_across, p_across) * 0.7
    bar = (
        cq.Workplane("XY")
        .box(bar_w, arm_len + 2.0, bar_h, centered=(True, True, False))
    )
    body = bar.union(stem_boss).union(post_boss)
    return body


def build_base_post():
    """The stand: a heavy filleted base plate with a vertical post rising from
    the centre. The reach arm's post clamp slips over this post. A wide, thick
    base resists tip-over."""
    base_depth = base_width * 0.7
    base_thick = max(10.0, wall * 2.2)

    base = (
        cq.Workplane("XY")
        .box(base_width, base_depth, base_thick, centered=(True, True, False))
    )
    try:
        base = base.edges("|Z").fillet(min(6.0, base_width * 0.12))
    except Exception:
        pass

    # Vertical post rising from the base centre, overlapping into the base.
    post = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, base_thick - 1.0))
        .circle(post_dia / 2.0)
        .extrude(post_height + 1.0)
    )
    body = base.union(post)

    # Four mount holes through the base corners (vented top↔bottom).
    ox = base_width / 2.0 - base_thick
    oy = base_depth / 2.0 - base_thick
    for sx in (-1, 1):
        for sy in (-1, 1):
            hole = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(sx * ox, sy * oy, -0.5))
                .circle(max(0.6, clamp_screw_d / 2.0 + 0.6))
                .extrude(base_thick + 1.0)
            )
            body = body.cut(hole)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "snug_arm":
    result = build_snug_arm()
elif target_part == "base_post":
    result = build_base_post()
else:
    result = build_stem_clamp()
