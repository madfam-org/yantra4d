"""
Wall Tile — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Interlocking decorative wall / acoustic tiles. Each tile is a square panel with a
tongue-and-groove interlock on its edges so tiles snap together edge-to-edge into a
seamless field. Pick a flat tile, a relief-pattern tile, or an acoustic tile whose
faceted sound-scatter blocks diffuse reflections.

Three parts (dispatched via `target_part`):
  * "flat_tile"     — a plain interlocking panel (the base for paint / wallpaper).
  * "relief_tile"   — a panel with a raised geometric relief pattern on its face.
  * "acoustic_tile" — a panel carrying a field of varying-height prisms (a quadratic-
                      residue-style diffuser) that scatters sound.

The INTERLOCK is the shared CDG: a tongue on two edges and a matching groove on the
other two, sized by `tile_size` and `interlock`, so any two tiles mate. All prismatic —
fast and watertight; the relief/scatter fields are built by a single compound boolean.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `tile_size`).
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
target_part = str(PARAM(lambda: target_part, "flat_tile"))  # flat_tile|relief_tile|acoustic_tile
pattern     = str(PARAM(lambda: pattern,     "grid"))       # grid|diagonal|concentric

tile_size = float(PARAM(lambda: tile_size, 100.0))   # tile edge length (mm, square)
base_t    = float(PARAM(lambda: base_t,      4.0))   # base panel thickness (mm)
interlock = float(PARAM(lambda: interlock,   6.0))   # tongue/groove size (mm)
relief_h  = float(PARAM(lambda: relief_h,    3.0))   # relief / scatter max height (mm)
fit       = float(PARAM(lambda: fit,         0.3))   # groove oversize for a snug snap (mm)
cells     = int(  PARAM(lambda: cells,         6))   # pattern subdivision per side

# Clamp inputs to sane ranges so extreme UI values still build watertight.
tile_size = max(40.0, min(tile_size, 250.0))
base_t    = max(2.0, min(base_t, 10.0))
interlock = max(3.0, min(interlock, min(20.0, tile_size * 0.2)))
relief_h  = max(1.0, min(relief_h, 12.0))
fit       = max(0.0, min(fit, 1.0))
cells     = max(2, min(cells, 10))

half = tile_size / 2.0


# ── Interlocking base panel (tongue on +X/+Y, groove on -X/-Y) ───────────────
def _interlock_panel():
    """A square panel with a tongue protruding on the +X and +Y edges and a matching
    groove cut into the -X and -Y edges, so tiles tile seamlessly. Built solid then the
    grooves are cut and tongues unioned."""
    panel = cq.Workplane("XY").box(tile_size, tile_size, base_t, centered=(True, True, False))
    t_len = tile_size * 0.6            # interlock runs along 60% of the edge (centred)
    # Tongues: thin bars protruding at mid-thickness on +X and +Y.
    tongue_x = (
        cq.Workplane("XY")
        .box(interlock, t_len, base_t * 0.5, centered=(True, True, False))
        .translate((half + interlock / 2.0 - 0.01, 0, base_t * 0.25))
    )
    tongue_y = (
        cq.Workplane("XY")
        .box(t_len, interlock, base_t * 0.5, centered=(True, True, False))
        .translate((0, half + interlock / 2.0 - 0.01, base_t * 0.25))
    )
    panel = panel.union(tongue_x).union(tongue_y)
    # Grooves: matching slots cut into the -X and -Y edges (oversized by `fit`), opening
    # on the outer face so a neighbour tile's tongue slides in.
    groove_x = (
        cq.Workplane("XY")
        .box(interlock + 0.5, t_len + fit, base_t * 0.5 + fit, centered=(True, True, False))
        .translate((-half + (interlock + 0.5) / 2.0 - 0.25, 0, base_t * 0.25))
    )
    groove_y = (
        cq.Workplane("XY")
        .box(t_len + fit, interlock + 0.5, base_t * 0.5 + fit, centered=(True, True, False))
        .translate((0, -half + (interlock + 0.5) / 2.0 - 0.25, base_t * 0.25))
    )
    panel = panel.cut(groove_x).cut(groove_y)
    try:
        panel = panel.clean()
    except Exception:
        pass
    return panel


# ── Relief / scatter fields (single compound boolean) ────────────────────────
def _relief_add():
    """A COMPOUND of raised relief prisms forming `pattern` on the tile face, unioned in
    ONE boolean. Returns a cq solid to union onto the panel, or None."""
    span = tile_size * 0.86
    step = span / cells
    x0 = -span / 2.0 + step / 2.0
    solids = []
    for i in range(cells):
        for j in range(cells):
            cx = x0 + i * step
            cy = x0 + j * step
            if pattern == "diagonal" and ((i + j) % 2 == 1):
                continue
            if pattern == "concentric":
                # height rings out from centre
                ring = max(abs(i - (cells - 1) / 2.0), abs(j - (cells - 1) / 2.0))
                if int(ring) % 2 == 1:
                    continue
            block = (
                cq.Workplane("XY")
                .center(cx, cy)
                .box(step * 0.7, step * 0.7, relief_h, centered=(True, True, False))
                .translate((0, 0, base_t))
            )
            solids.append(block.val())
    if not solids:
        return None
    return cq.Compound.makeCompound(solids)


def _scatter_add():
    """A COMPOUND of varying-height prisms (a pseudo quadratic-residue diffuser) unioned
    in ONE boolean. Heights follow a residue sequence so the field scatters sound."""
    span = tile_size * 0.9
    step = span / cells
    x0 = -span / 2.0 + step / 2.0
    prime = 7
    solids = []
    for i in range(cells):
        for j in range(cells):
            cx = x0 + i * step
            cy = x0 + j * step
            res = ((i * i + j * j) % prime)          # quadratic-residue-style well index
            h = relief_h * (0.25 + 0.75 * res / (prime - 1))
            block = (
                cq.Workplane("XY")
                .center(cx, cy)
                .box(step * 0.86, step * 0.86, h, centered=(True, True, False))
                .translate((0, 0, base_t))
            )
            solids.append(block.val())
    if not solids:
        return None
    return cq.Compound.makeCompound(solids)


# ── Part builders ─────────────────────────────────────────────────────────────
def build_flat_tile():
    """A plain interlocking panel."""
    return _interlock_panel()


def build_relief_tile():
    """The interlocking panel with a raised relief pattern fused onto the face."""
    panel = _interlock_panel()
    add = _relief_add()
    if add is not None:
        panel = panel.union(add)
    return panel


def build_acoustic_tile():
    """The interlocking panel with a sound-scattering diffuser field fused on."""
    panel = _interlock_panel()
    add = _scatter_add()
    if add is not None:
        panel = panel.union(add)
    return panel


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "relief_tile":
    result = build_relief_tile()
elif target_part == "acoustic_tile":
    result = build_acoustic_tile()
else:
    result = build_flat_tile()
