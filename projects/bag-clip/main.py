"""
Sprung Bag / Chip Clip — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A one-piece C-clamp that reseals bags. The clip's side cross-section is a single
C profile: a curved back spine joins an upper and a lower jaw, and the jaws pinch
together at the mouth. The whole profile is extruded once across the clip width,
so the part is inherently watertight. The back spine (beam) thickness acts as a
living spring — squeeze the tails, the mouth opens; release and the printed beam
clamps the bag. An optional snap-hook catch latches the jaw tips closed for
thicker / heavier bags.

Modes (dispatched via `target_part`):
  * "clip"      — the default clip at `clip_width`.
  * "wide_clip" — a wider clip (1.8x width) for cereal / freezer bags, same
                  profile so a family of sizes shares one grip geometry.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `clip_width`).
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


# ── Parameters ───────────────────────────────────────────────────────────────
clip_width  = float(PARAM(lambda: clip_width,   40.0))   # jaw width (mm, along Y)
jaw_length  = float(PARAM(lambda: jaw_length,   28.0))   # jaw reach from spine (mm, along X)
beam_thick  = float(PARAM(lambda: beam_thick,    2.4))   # spring/beam wall thickness (mm)
mouth_gap   = float(PARAM(lambda: mouth_gap,     1.2))   # resting gap at the jaw tips (mm)
jaw_height  = float(PARAM(lambda: jaw_height,   12.0))   # overall clip height (mm, along Z)
catch       = str(  PARAM(lambda: catch,   "friction"))  # "friction" | "snap-hook"
grip_teeth  = bool( PARAM(lambda: grip_teeth,   True))   # ribs on the gripping faces
tail_len    = float(PARAM(lambda: tail_len,      8.0))   # finger tails past the spine (mm)

target_part = str(  PARAM(lambda: target_part, "clip"))  # "clip" | "wide_clip"


# ── Derived / clamped geometry ───────────────────────────────────────────────
if target_part == "wide_clip":
    clip_width = clip_width * 1.8

clip_width = max(8.0, clip_width)
jaw_length = max(8.0, jaw_length)
jaw_height = max(6.0, jaw_height)
# Keep the beam springy but printable and never thicker than half the throat.
beam_thick = max(1.2, min(beam_thick, (jaw_height - 1.5) / 2.0, jaw_length * 0.5))
tail_len = max(0.0, tail_len)

# Throat (open span between the two jaws at the spine) and the closing wedge.
throat = jaw_height - 2.0 * beam_thick
# Never let the tips fully touch (zero-thickness contact breaks watertightness);
# keep at least a 0.4 mm printed mouth so the clip stays a clean single solid.
mouth_gap = max(0.4, min(mouth_gap, throat))
# Each jaw tip rises/drops by `close` so the resting tip gap == mouth_gap.
close = max(0.0, (throat - mouth_gap) / 2.0)


# ── Side profile (XZ plane) ──────────────────────────────────────────────────
def clip_profile():
    """Closed polyline of the clip's side cross-section, then extruded across Y.

    Coordinates: x = along the jaws (spine at x=0, tips at +x), z = height.
    Built as one outline traced clockwise from the lower-outer corner. The
    interior throat is created by the jaw undersides meeting the wedge, so the
    single extruded profile is a watertight solid with the C-shaped mouth.
    """
    x_tip = jaw_length
    x_tail = -tail_len
    z_top = jaw_height
    bt = beam_thick

    # Trace the outline. Start bottom-left (tail), go clockwise.
    pts = [
        (x_tail, 0.0),          # lower tail outer-bottom
        (x_tip, 0.0),           # lower jaw outer-bottom, to the tip
        (x_tip, bt),            # up the lower tip face
        (x_tip - min(jaw_length * 0.6, 14.0), bt),  # back along lower jaw top
        # rise into the throat to close the mouth by `close`
        (x_tip, bt + close),                        # lower wedge crest at tip
    ]
    # If the wedge is degenerate (mouth fully open), skip the crest weirdness.
    if close <= 0.05:
        pts = [
            (x_tail, 0.0),
            (x_tip, 0.0),
            (x_tip, bt),
        ]
        # lower jaw top runs flat back to the spine inner corner
        pts += [(0.0 + bt, bt)]
        pts += [(bt, z_top - bt)]          # up the spine inner wall
        pts += [(x_tip, z_top - bt)]       # upper jaw underside out to tip
        pts += [(x_tip, z_top)]            # up the upper tip face
        pts += [(x_tail, z_top)]           # back across upper jaw top to tail
        return pts

    # Mouth partially closed: lower jaw underside steps up to the crest then
    # back down to the spine inner corner, forming the pinch.
    pts = [
        (x_tail, 0.0),
        (x_tip, 0.0),
        (x_tip, bt + close),               # lower tip incl. wedge crest
        (bt, bt),                          # underside back to spine inner corner
        (bt, z_top - bt),                  # up the spine inner wall
        (x_tip, z_top - bt - close),       # upper underside out toward tip (drops by close)
        (x_tip, z_top),                    # up the upper tip face
        (x_tail, z_top),                   # across the upper jaw top back to tail
    ]
    return pts


def build_clip():
    pts = clip_profile()
    body = (
        cq.Workplane("XZ")
        .polyline(pts).close()
        .extrude(clip_width)
        .translate((0, clip_width / 2.0, 0))  # center across the width
    )

    # Comfort fillets are kept strictly smaller than the thinnest local feature
    # (beam, mouth gap) so a fillet can never chew through a thin jaw / the mouth
    # and turn the solid non-manifold. On very thin clips we skip them entirely.
    edge_r = min(beam_thick * 0.4, mouth_gap * 0.35, throat * 0.3, 0.6)
    if edge_r >= 0.25:
        # Outer back-spine corner (stress relief on the spring).
        try:
            body = body.edges("|Y and <X").fillet(edge_r)
        except Exception:
            pass

    # Grip ribs: shallow ridges across the width on both jaw inner faces.
    if grip_teeth:
        body = _add_ribs(body)

    # Snap-hook catch at the tips (solid features; user flexes them past).
    if catch == "snap-hook":
        body = _add_snap(body)

    return body


def _add_ribs(body):
    """Union a few slim cross-width ridges onto the inner faces of both jaws.

    Each rib overlaps its jaw solid (base set 0.1 mm inside the jaw) and rises
    into the throat. Rib height is clamped to a fraction of the throat so it can
    never span the whole gap and touch the opposing jaw (which would fuse the
    mouth and, at coincident faces, break the manifold)."""
    rib_w = 0.8
    rib_h = min(0.8, max(0.3, throat * 0.25))
    n = 3
    reach = jaw_length - 5.0
    if reach <= rib_w * (n + 1):
        return body
    step = reach / (n + 1)
    yw = clip_width  # full width so side faces stay coplanar with the body
    lower_top = beam_thick
    upper_under = jaw_height - beam_thick
    for i in range(1, n + 1):
        x = beam_thick + i * step
        # Lower rib: base 0.1 inside the lower jaw, points up into the throat.
        low = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(x, 0.0, lower_top - 0.1))
            .box(rib_w, yw, rib_h + 0.1, centered=(True, True, False))
        )
        # Upper rib: overlaps into the upper jaw (top 0.1 mm inside it) and
        # points DOWN into the throat.
        up = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(x, 0.0, upper_under - rib_h))
            .box(rib_w, yw, rib_h + 0.1, centered=(True, True, False))
            .translate((0, 0, 0.1))
        )
        body = body.union(low).union(up)
    return body


def _add_snap(body):
    """A latch: an L-shaped hook rising from the LOWER jaw tip whose lip reaches
    back over the throat, plus a catch ridge embedded in the UPPER jaw underside.
    Both are single extruded profiles / embedded boxes that solidly interpenetrate
    the jaws, so the union stays watertight across the whole parameter range.

    Sizes are clamped to the available throat so the hook never pokes into open
    air above the upper jaw (which would break the manifold)."""
    x_tip = jaw_length
    yw = clip_width  # span the full width so side faces stay coplanar w/ the body

    # How tall the hook may rise: at most to just below the upper jaw underside.
    upper_under = jaw_height - beam_thick
    max_rise = max(0.0, upper_under - beam_thick - 0.6)
    rise = min(3.2, max_rise)
    if rise < 1.0:
        return body  # throat too small for a latch — leave it a friction clip

    lip_over = min(2.4, jaw_length * 0.4)  # how far the lip reaches back over throat
    # L-hook profile in XZ: a post at the tip + a lip cantilevering back (−x).
    base_z = beam_thick - 0.4  # start below the jaw top so it fuses with the jaw
    hpts = [
        (x_tip - 1.6, base_z),
        (x_tip, base_z),
        (x_tip, base_z + rise),
        (x_tip - lip_over, base_z + rise),
        (x_tip - lip_over, base_z + rise - 1.0),
        (x_tip - 1.6, base_z + rise - 1.0),
    ]
    hook = (
        cq.Workplane("XZ")
        .polyline(hpts).close()
        .extrude(yw)
        .translate((0, yw / 2.0, 0))
    )
    body = body.union(hook)

    # Catch ridge on the upper jaw underside — a box embedded UP into the upper
    # jaw solid (base at the underside, extending into the jaw), never below it.
    ridge_h = min(1.4, beam_thick - 0.4)
    if ridge_h > 0.3:
        ridge = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(x_tip - lip_over - 0.8, 0.0, upper_under - 0.1))
            .box(2.0, yw, ridge_h + 0.1, centered=(True, True, False))
        )
        body = body.union(ridge)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
result = build_clip()
