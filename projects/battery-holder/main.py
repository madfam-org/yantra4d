"""
Battery Holder — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Cell holders that keep a set of cells captive in a printed carrier for a battery
pack, with open contact slots at each end so bus strips or spring contacts can
reach the terminals. Pick the cell chemistry/size and the bores land on the real
cell diameter; the array is laid out on a pitch that leaves a printable wall
between cells.

Modes are dispatched via `target_part`:
  * "holder"        — a block of cell bores in a row, with end contact slots.
  * "spacer"        — a thin spacer grid (rings only) that indexes a pack's cells.
  * "series_holder" — a two-row holder wired for a series pack (alternating ends).

Cell sizes (diameter × length, mm): 18650, 21700, AA, AAA.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `cell`).
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


# ── Cell table (nominal outer diameter and length, mm) ───────────────────────
_CELLS = {
    "18650": {"dia": 18.4, "len": 65.0},
    "21700": {"dia": 21.2, "len": 70.0},
    "AA":    {"dia": 14.5, "len": 50.5},
    "AAA":   {"dia": 10.5, "len": 44.5},
}


def cell_spec(key):
    k = str(key).strip().upper().replace(" ", "")
    if k in ("18650",):
        return _CELLS["18650"]
    if k in ("21700",):
        return _CELLS["21700"]
    if k in ("AA",):
        return _CELLS["AA"]
    if k in ("AAA",):
        return _CELLS["AAA"]
    return _CELLS["18650"]


# ── Parameters ───────────────────────────────────────────────────────────────
cell       = str(  PARAM(lambda: cell,      "18650"))   # 18650|21700|AA|AAA
count      = int(  PARAM(lambda: count,          4))    # cells in a row
clearance  = float(PARAM(lambda: clearance,    0.5))    # per-side bore clearance
wall       = float(PARAM(lambda: wall,         2.0))    # wall between/around cells
floor      = float(PARAM(lambda: floor,        1.6))    # bottom thickness under cells
bore_depth = float(PARAM(lambda: bore_depth,  0.55))    # fraction of cell length cradled
contact_w  = float(PARAM(lambda: contact_w,    8.0))    # end contact-slot width

target_part = str(PARAM(lambda: target_part, "holder"))

# ── Derived ──────────────────────────────────────────────────────────────────
spec = cell_spec(cell)
cell_d = spec["dia"]
cell_len = spec["len"]

count = max(1, min(count, 12))
clearance = max(0.1, min(clearance, 1.5))
wall = max(1.2, min(wall, 6.0))
floor = max(1.0, min(floor, 6.0))
bore_depth = max(0.3, min(bore_depth, 0.95))
contact_w = max(3.0, min(contact_w, cell_d))

bore_d = cell_d + 2.0 * clearance
pitch = bore_d + wall
cradle_h = cell_len * bore_depth            # how deep the trough cradles the cell
block_h = floor + cradle_h


# ── Helpers ──────────────────────────────────────────────────────────────────
def _row_x(n):
    """Centred X positions for n cells on `pitch`."""
    x0 = -(n - 1) * pitch / 2.0
    return [x0 + i * pitch for i in range(n)]


def _block(n_cols, n_rows):
    w = n_cols * pitch + wall
    d = n_rows * (cell_len + 2.0 * wall)
    body = cq.Workplane("XY").box(w, d, block_h, centered=(True, True, False))
    try:
        body = body.edges("|Z").fillet(min(2.5, wall))
    except Exception:
        pass
    return body, w, d


def _cut_cell_troughs(body, xs, y_centre):
    """Cut a horizontal cylindrical trough (cell cradle) along Y at each x. Built
    as one grouped cut so a dense row stays fast and watertight."""
    z_axis = floor + bore_d / 2.0
    cutters = (
        cq.Workplane("XZ").workplane(offset=y_centre + (cell_len / 2.0 + 1.0))
        .pushPoints([(x, z_axis) for x in xs])
        .circle(bore_d / 2.0).extrude(cell_len + 2.0)
    )
    return body.cut(cutters)


def _cut_contacts(body, xs, y_end):
    """End contact slots: a rectangular window at each cell end so a bus strip or
    spring reaches the terminal. `y_end` is the +Y (or -Y) wall centre."""
    z_axis = floor + bore_d / 2.0
    for sy in (-1.0, 1.0):
        cutters = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, sy * y_end, z_axis))
            .pushPoints([(x, 0.0) for x in xs])
            .box(contact_w, wall + 4.0, contact_w, centered=(True, True, True))
        )
        body = body.cut(cutters)
    return body


# ── Builders ─────────────────────────────────────────────────────────────────
def build_holder():
    xs = _row_x(count)
    body, w, d = _block(count, 1)
    body = _cut_cell_troughs(body, xs, 0.0)
    body = _cut_contacts(body, xs, cell_len / 2.0 + wall / 2.0)
    return body


def build_spacer():
    """A thin spacer grid: just the inter-cell webbing (rings) at one height, no
    full-length cradle — it indexes cell spacing in a shrink-wrapped pack."""
    xs = _row_x(count)
    ring_h = max(4.0, cell_d * 0.35)
    w = count * pitch + wall
    d = cell_d + 2.0 * wall
    body = cq.Workplane("XY").box(w, d, ring_h, centered=(True, True, False))
    try:
        body = body.edges("|Z").fillet(min(2.0, wall))
    except Exception:
        pass
    # Bore each cell hole THROUGH (a spacer plate the cells pass through).
    holes = (
        cq.Workplane("XY").pushPoints([(x, 0.0) for x in xs])
        .circle(bore_d / 2.0).extrude(ring_h + 1.0).translate((0, 0, -0.5))
    )
    body = body.cut(holes)
    return body


def build_series_holder():
    """Two rows of cells for a series pack; contact windows at alternating ends
    invite a folded bus strip that walks + to - down the pack."""
    xs = _row_x(count)
    n_rows = 2
    body, w, d = _block(count, n_rows)
    row_dy = (cell_len + 2.0 * wall) / 2.0
    for r, yc in enumerate((-row_dy, row_dy)):
        body = _cut_cell_troughs_row(body, xs, yc)
        # alternate the contact-window end per row for a series daisy chain
        body = _cut_contacts_row(body, xs, yc, cell_len / 2.0)
    return body


def _cut_cell_troughs_row(body, xs, y_centre):
    z_axis = floor + bore_d / 2.0
    cutters = (
        cq.Workplane("XZ").workplane(offset=y_centre + (cell_len / 2.0 + 1.0))
        .pushPoints([(x, z_axis) for x in xs])
        .circle(bore_d / 2.0).extrude(cell_len + 2.0)
    )
    return body.cut(cutters)


def _cut_contacts_row(body, xs, y_centre, half_len):
    z_axis = floor + bore_d / 2.0
    for sy in (-1.0, 1.0):
        cutters = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, y_centre + sy * half_len, z_axis))
            .pushPoints([(x, 0.0) for x in xs])
            .box(contact_w, wall + 4.0, contact_w, centered=(True, True, True))
        )
        body = body.cut(cutters)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
_dispatch = {
    "holder": build_holder,
    "spacer": build_spacer,
    "series_holder": build_series_holder,
}

result = _dispatch.get(target_part, build_holder)()
