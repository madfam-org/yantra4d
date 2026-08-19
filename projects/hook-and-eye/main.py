"""
Hook & Eye — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The oldest garment fastener: a sprung hook that catches an eye (loop or bar).
Parametric across the two places it lives — a single tailoring hook-and-bar at a
waistband or neck, and the multi-column, multi-row hook-and-eye TAPE that closes a
bra band (the "N×M" closure: N columns of adjustment × M rows of hooks). This is
the solid the Fashion Cabinet `bra-wireless` (and any hook-closed garment) notion
bridges to; the garment cartridge owns the band/placement math, this owns the
hardware.

Modes (dispatched via `target_part`):
  * "hook"      — a single flat hook: a plate with two sewing eyelets and a curled
                  hook nose that springs over a bar.
  * "eye"       — the mate: a plate with two sewing eyelets and a raised bar (or a
                  round eye loop) the hook catches.
  * "bra_tape"  — a hook plate and an eye plate carrying an N-column × M-row grid
                  of hooks/eyes, the standard bra-back closure with `columns`
                  positions of band adjustment. Returned as an Assembly.

Every part is a watertight solid. The hook nose is a half-torus curl (built from
makeTorus primitives, not a fragile swept arc), fused to the plate by volumetric
overlap.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `columns`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr.
  - Assign the final result to a top-level name `result`.
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
columns    = int(  PARAM(lambda: columns,     3))      # bra-tape adjustment columns (N)
rows       = int(  PARAM(lambda: rows,        2))      # bra-tape hook rows (M)
size_mm    = float(PARAM(lambda: size_mm,     7.0))    # nominal hook width / bar length (mm)
plate_t    = float(PARAM(lambda: plate_t,     1.6))    # plate thickness (mm)
wire_d     = float(PARAM(lambda: wire_d,      1.6))    # hook/bar wire diameter (mm)
gap        = float(PARAM(lambda: gap,         0.35))   # hook-to-bar print clearance (mm)

target_part = str( PARAM(lambda: target_part, "bra_tape"))  # hook|eye|bra_tape

# ── Safe clamps ──────────────────────────────────────────────────────────────
columns = max(1, min(columns, 6))
rows    = max(1, min(rows, 4))
size_mm = max(4.0, min(size_mm, 20.0))
plate_t = max(1.0, min(plate_t, 3.0))
wire_d  = max(1.0, min(wire_d, 4.0))
gap     = max(0.15, min(gap, 0.8))

_col_pitch = size_mm * 2.2      # spacing between adjustment columns (mm)
_row_pitch = size_mm * 2.4      # spacing between hook rows (mm)
_plate_pad = size_mm * 1.1      # plate margin around the hooks/eyes


# ── Helpers ───────────────────────────────────────────────────────────────────
def _plate(w, h, t):
    """A rounded sewing plate on XY, base z=0, centred in X/Y."""
    p = cq.Workplane("XY").box(w, h, t, centered=(True, True, False))
    r = min(w, h) * 0.18
    try:
        p = p.edges("|Z").fillet(r)
    except Exception:
        pass
    return p


def _sew_eyelets(plate, w, h, t):
    """Cut two sewing eyelets near one long edge of a plate."""
    er = max(0.6, wire_d * 0.5)
    ey = -h / 2.0 + er + 1.0
    for ex in (-w / 4.0, w / 4.0):
        hole = (
            cq.Workplane("XY")
            .center(ex, ey)
            .circle(er)
            .extrude(t + 2.0)
            .translate((0, 0, -1.0))
        )
        plate = plate.cut(hole)
    return plate


def _hook_nose(cx, cy, z0):
    """A curled hook rising off the plate at (cx, cy): a post carrying a half-torus
    curl of wire that a bar springs into, opening toward -Y so a bar drops in from
    the front. Built from revolve/torus primitives (boolean-robust — no fragile
    swept arcs), fused to the plate by sinking the post into it. One solid."""
    r_curl = size_mm * 0.5           # curl centreline radius
    post_h = z0 + r_curl             # post rises to the curl's axis height
    # Vertical post from the plate up to the curl axis.
    post = (
        cq.Workplane("XY")
        .center(cx, cy)
        .circle(wire_d / 2.0)
        .extrude(post_h)
        .translate((0, 0, -0.4))     # sink into the plate for a solid fuse
    )
    # The curl: a full torus of tube-radius wire_d/2 and centreline radius r_curl,
    # revolved about a horizontal (X) axis so its plane is vertical (YZ), then the
    # rear half cut away to leave an open C facing -Y. makeTorus is watertight.
    torus = cq.Solid.makeTorus(
        r_curl, wire_d / 2.0,
        pnt=cq.Vector(cx, cy, post_h),
        dir=cq.Vector(1, 0, 0),      # torus axis along X → ring lies in the YZ plane
    )
    curl = cq.Workplane(obj=torus)
    # Cut the +Y rear half so the hook opens toward -Y (a bar enters from the front).
    back_cut = (
        cq.Workplane("XY")
        .box(r_curl * 3, r_curl * 3, r_curl * 3, centered=(True, False, True))
        .translate((cx, cy, post_h))
    )
    curl = curl.cut(back_cut)
    return post.union(curl)


def _eye_bar(cx, cy, z0):
    """A raised bar the hook catches: a short wire segment bridged above the plate
    on two posts (a staple), lying along X. One solid."""
    span = size_mm * 0.9
    height = wire_d * 1.6 + gap
    posts = None
    for px in (cx - span / 2.0, cx + span / 2.0):
        post = (
            cq.Workplane("XY")
            .center(px, cy)
            .circle(wire_d / 2.0)
            .extrude(z0 + height)
            .translate((0, 0, -0.4))
        )
        posts = post if posts is None else posts.union(post)
    bar = (
        cq.Workplane("YZ")
        .center(cy, z0 + height)
        .circle(wire_d / 2.0)
        .extrude(span, both=True)
        .translate((cx, 0, 0))
    )
    return posts.union(bar)


def build_hook_plate(n_cols, n_rows):
    """A sewing plate carrying an n_cols × n_rows grid of hook noses."""
    w = max(size_mm * 2.2, (n_cols - 1) * _col_pitch + 2 * _plate_pad)
    h = max(size_mm * 2.2, (n_rows - 1) * _row_pitch + 2 * _plate_pad)
    plate = _plate(w, h, plate_t)
    plate = _sew_eyelets(plate, w, h, plate_t)
    x0 = -(n_cols - 1) * _col_pitch / 2.0
    y0 = (n_rows - 1) * _row_pitch / 2.0
    for c in range(n_cols):
        for r in range(n_rows):
            plate = plate.union(_hook_nose(x0 + c * _col_pitch, y0 - r * _row_pitch, plate_t))
    return plate


def build_eye_plate(n_cols, n_rows):
    """A sewing plate carrying an n_cols × n_rows grid of eye bars — the mate to
    the hook plate (columns give band-size adjustment)."""
    w = max(size_mm * 2.2, (n_cols - 1) * _col_pitch + 2 * _plate_pad)
    h = max(size_mm * 2.2, (n_rows - 1) * _row_pitch + 2 * _plate_pad)
    plate = _plate(w, h, plate_t)
    plate = _sew_eyelets(plate, w, h, plate_t)
    x0 = -(n_cols - 1) * _col_pitch / 2.0
    y0 = (n_rows - 1) * _row_pitch / 2.0
    for c in range(n_cols):
        for r in range(n_rows):
            plate = plate.union(_eye_bar(x0 + c * _col_pitch, y0 - r * _row_pitch, plate_t))
    return plate


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "hook":
    result = build_hook_plate(1, rows)
elif target_part == "eye":
    result = build_eye_plate(1, rows)
else:  # bra_tape — hook plate (1 row of hooks) + eye plate (N columns of adjustment)
    hook = build_hook_plate(1, rows)
    eye = build_eye_plate(columns, rows)
    asm = cq.Assembly()
    # Park the two plates side by side for preview (as they'd sit unhooked).
    hook_w = max(size_mm * 2.2, 2 * _plate_pad)
    eye_w = max(size_mm * 2.2, (columns - 1) * _col_pitch + 2 * _plate_pad)
    asm.add(hook.translate((-(hook_w + eye_w) / 2.0 - 3.0, 0, 0)),
            name="hook_plate", color=cq.Color("#b8a1c8"))
    asm.add(eye, name="eye_plate", color=cq.Color("#c8b1d8"))
    result = asm
