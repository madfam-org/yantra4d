"""
PC Fan Filter Frame — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A dust filter frame for standard PC / printer fans. It sits on the fan's intake
face on the same corner-hole square the fan uses, holding a snap-in mesh over the
airflow bore so lint and dust never reach the fan. The frame carries a printed
retaining grille so the filter media (a cut disc of nylon/steel mesh or foam) is
captured without glue.

A fan table gives the correct corner-hole spacing and open bore for each size, so
the frame drops onto the same fan a fan-adapter or dust-shroud bolts to:
  40 / 60 / 80 / 120 / 140 mm  (spacing 32 / 50 / 71.5 / 105 / 124.5 mm).

Three modes, each its own studio part (a single manifold solid):
  * filter_frame  — the screw-mount frame: a square flange with the four fan
                    corner holes, a media pocket, and a printed retaining grille.
  * magnet_frame  — a screwless variant: the same media pocket + grille, but the
                    corner holes are replaced by four magnet pockets so the frame
                    clicks onto a steel fan grill or a magnet ring.
  * stacked_filter — a taller two-stage cartridge: a coarse outer grille and a
                    fine inner grille separated by a spacer wall, capturing two
                    media layers (pre-filter + fine) in one printed part.

Watertight strategy:
  Every part is built by UNIONING overlapping solids (frame ring + grille bars +
  hub) — never by cutting a fragile web. The airflow bore is a through-window that
  vents to outside, so no sealed cavity forms. Corner holes and magnet pockets are
  bored last. Fillets clean the blank BEFORE feature cuts, wrapped in try/except.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  `cq` and `math` are pre-injected globals; manifest parameters arrive as bare
  globals (e.g. `target_part`). Read them via PARAM(lambda: name, default).
  Assign the final solid to a top-level name `result`.
"""

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default. `except Exception`
    catches the NameError the sandbox raises for an unbound parameter name."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── PC-fan table (real corner-hole squares) ──────────────────────────────────
# body    : nominal fan size (mm, square)
# spacing : corner mounting-hole centre-to-centre distance (mm)
# bore    : largest open airflow circle for that fan (mm)
# screw   : corner-hole clearance diameter (mm, for M3/M4 self-tappers)
FAN_TABLE = {
    "40mm":  {"body": 40.0,  "spacing": 32.0,  "bore": 37.0,  "screw": 3.2},
    "60mm":  {"body": 60.0,  "spacing": 50.0,  "bore": 57.0,  "screw": 4.3},
    "80mm":  {"body": 80.0,  "spacing": 71.5,  "bore": 77.0,  "screw": 4.3},
    "120mm": {"body": 120.0, "spacing": 105.0, "bore": 117.0, "screw": 4.5},
    "140mm": {"body": 140.0, "spacing": 124.5, "bore": 137.0, "screw": 4.5},
}


def fan_spec(name):
    return FAN_TABLE.get(str(name).strip(), FAN_TABLE["120mm"])


# ── Parameters ────────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "filter_frame"))
# "filter_frame" | "magnet_frame" | "stacked_filter"

fan_size = str(PARAM(lambda: fan_size, "120mm"))   # 40|60|80|120|140 mm
frame_h = float(PARAM(lambda: frame_h, 6.0))       # frame body height (Z, mm)
media_pocket = float(PARAM(lambda: media_pocket, 3.0))  # media pocket depth (mm)
grille_bar = float(PARAM(lambda: grille_bar, 2.2))  # grille bar width (mm)
grille_rings = int(PARAM(lambda: grille_rings, 3))  # concentric retaining rings
magnet_dia = float(PARAM(lambda: magnet_dia, 8.0))  # magnet pocket diameter (mm)
magnet_h = float(PARAM(lambda: magnet_h, 3.0))      # magnet pocket depth (mm)

# Clamp to sane ranges so extreme UI values never crash the kernel.
frame_h = max(4.0, min(frame_h, 16.0))
media_pocket = max(1.5, min(media_pocket, frame_h - 2.0))
grille_bar = max(1.4, min(grille_bar, 4.0))
grille_rings = max(1, min(grille_rings, 6))
magnet_dia = max(4.0, min(magnet_dia, 14.0))
magnet_h = max(1.5, min(magnet_h, min(6.0, frame_h - 1.5)))

spec = fan_spec(fan_size)
body = spec["body"]
spacing = spec["spacing"]
bore = spec["bore"]
screw = spec["screw"]

bore_r = bore / 2.0
inset = max(screw / 2.0 + 2.0, 4.0)   # corner-hole inset from the fan edge


# ── Shared helpers ───────────────────────────────────────────────────────────
def _fillet_z(solid, r):
    try:
        return solid.edges("|Z").fillet(r)
    except Exception:
        return solid


def solid_ring(mid_r, width, z0, height):
    """A flat annular ring wall, centred, spanning [z0, z0+height]."""
    outer = mid_r + width / 2.0
    inner = max(0.4, mid_r - width / 2.0)
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z0))
        .circle(outer).circle(inner)
        .extrude(height)
    )


def retaining_grille(z0, height, inner_bore_r, rings=None):
    """A printed retaining grille that spans the bore so the media disc is held:
    a hub, `rings` concentric rings, and four cross spokes. All solids, unioned,
    sitting on z0. Returns the grille solid."""
    bw = grille_bar
    n_rings = grille_rings if rings is None else rings
    # Rim ring right at the bore edge closes the window frame-side.
    g = solid_ring(inner_bore_r - bw / 2.0, bw, z0, height)
    # Concentric rings from a small hub out toward the bore.
    hub_r = max(bw, inner_bore_r * 0.12)
    span = inner_bore_r - bw - hub_r
    if span > bw and n_rings >= 1:
        for i in range(n_rings):
            frac = (i + 1) / (n_rings + 1)
            rr = hub_r + span * frac
            g = g.union(solid_ring(rr, bw, z0, height))
    # Central hub disc.
    hub = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z0))
        .circle(hub_r).extrude(height)
    )
    g = g.union(hub)
    # Four cross spokes tying hub -> rim.
    for ang in (0.0, 90.0):
        spoke = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, z0))
            .rect(inner_bore_r * 2.0, bw)
            .extrude(height)
            .rotate((0, 0, 0), (0, 0, 1), ang)
        )
        g = g.union(spoke)
    # Trim the spokes/rings to the bore circle so nothing overhangs the window.
    keep = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z0 - 0.5))
        .circle(inner_bore_r).extrude(height + 1.0)
    )
    return g.intersect(keep)


def base_frame(height):
    """The square frame blank with a rounded outline and the open airflow bore,
    filleted on the vertical edges. Returns (solid, half)."""
    half = body / 2.0
    blank = (
        cq.Workplane("XY")
        .box(body, body, height, centered=(True, True, False))
    )
    blank = _fillet_z(blank, min(6.0, inset * 0.9))
    win = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -0.5))
        .circle(bore_r).extrude(height + 1.0)
    )
    return blank.cut(win), half


def corner_holes(solid, height, dia):
    """Bore the four fan corner holes through the frame (vents both faces)."""
    h = spacing / 2.0
    tool = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -0.5))
        .pushPoints([(h, h), (-h, h), (h, -h), (-h, -h)])
        .circle(dia / 2.0)
        .extrude(height + 1.0)
    )
    return solid.cut(tool)


def magnet_pockets(solid, height):
    """Blind magnet pockets at the four corners, open to the bottom face only
    (a magnet drops in from the print bed side). Opens to outside → vents."""
    h = spacing / 2.0
    tool = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -0.01))
        .pushPoints([(h, h), (-h, h), (h, -h), (-h, -h)])
        .circle(magnet_dia / 2.0)
        .extrude(magnet_h + 0.01)
    )
    return solid.cut(tool)


# ── Part builders ─────────────────────────────────────────────────────────────
def build_filter_frame():
    """Screw-mount filter frame: square flange with the four fan corner holes, a
    recessed media pocket, and a retaining grille that captures the media disc."""
    frame, _ = base_frame(frame_h)
    # Grille sits at the very bottom, capturing the media above it.
    grille = retaining_grille(0.0, frame_h - media_pocket, bore_r)
    frame = frame.union(grille)
    frame = corner_holes(frame, frame_h, screw)
    return frame


def build_magnet_frame():
    """Screwless magnetic frame: the same grille + media pocket, but the corners
    carry blind magnet pockets instead of screw holes so it clicks on magnetically."""
    frame, _ = base_frame(frame_h)
    grille = retaining_grille(0.0, frame_h - media_pocket, bore_r)
    frame = frame.union(grille)
    frame = magnet_pockets(frame, frame_h)
    return frame


def build_stacked_filter():
    """Two-stage cartridge: a taller frame with a coarse outer grille at the base
    and a fine inner grille partway up, separated by a ledge, so a pre-filter and
    a fine filter stack in one printed part. Screw-mounted."""
    h = frame_h + media_pocket + 3.0     # taller to hold two media layers
    frame, _ = base_frame(h)
    # Coarse grille at the bottom (fewer, wider rings) — the pre-filter stage.
    coarse_rings = max(1, grille_rings - 1)
    frame = frame.union(retaining_grille(0.0, 2.0, bore_r, rings=coarse_rings))
    # Divider ledge partway up: a narrow ring shelf the fine media rests on.
    mid_z = (h - 2.5) * 0.55
    frame = frame.union(solid_ring(bore_r - grille_bar, grille_bar * 1.4, mid_z, 2.0))
    # Fine grille just above the ledge (more, tighter rings) — the fine stage.
    fine_rings = min(6, grille_rings + 2)
    frame = frame.union(retaining_grille(mid_z + 2.0, 2.0, bore_r, rings=fine_rings))
    frame = corner_holes(frame, h, screw)
    return frame


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "magnet_frame":
    result = build_magnet_frame()
elif target_part == "stacked_filter":
    result = build_stacked_filter()
else:
    result = build_filter_frame()
