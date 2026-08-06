"""
Threaded Insert / Boss — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A mounting boss sized for a heat-set threaded insert (or a self-tapping screw).
The boss is a cylinder with an insert-sized bore; a soldering iron melts the brass
insert flush into the bore, giving a reusable metal thread in a printed part.

Insert-hole diameters follow common heat-set inserts (e.g. CNC Kitchen / Ruthex
style tapered inserts). The bore is deliberately a touch UNDER the insert OD so
the melted brass grips the plastic:

    Size   Insert-hole Ø   Screw clear Ø (self-tap fallback)
    M2     3.2 mm          2.4 mm
    M2.5   3.5 mm          3.0 mm
    M3     4.0 mm          3.4 mm
    M4     5.6 mm          4.5 mm
    M5     6.4 mm          5.5 mm
    M6     8.0 mm          6.6 mm

Three parts (dispatched via `target_part`):
  * "boss"        — a single boss with a base flange to glue/screw down (standalone)
                    or a wall segment (in_wall), per `mount`.
  * "boss_ribbed" — the same boss reinforced with gusset ribs.
  * "boss_strip"  — a row of N bosses at a pitch on a common base.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `insert_size`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr.
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


# ── Heat-set insert table ────────────────────────────────────────────────────
# insert_hole: bore diameter for a heat-set insert (brass melts in and grips).
# screw_clear: clearance-hole diameter if used as a plain self-tapping-screw boss.
# min_boss_od: a sensible minimum boss outer diameter for adequate wall.
INSERT_TABLE = {
    "M2":   {"insert_hole": 3.2, "screw_clear": 2.4, "min_boss_od": 6.0},
    "M2.5": {"insert_hole": 3.5, "screw_clear": 3.0, "min_boss_od": 6.5},
    "M3":   {"insert_hole": 4.0, "screw_clear": 3.4, "min_boss_od": 7.0},
    "M4":   {"insert_hole": 5.6, "screw_clear": 4.5, "min_boss_od": 9.0},
    "M5":   {"insert_hole": 6.4, "screw_clear": 5.5, "min_boss_od": 10.5},
    "M6":   {"insert_hole": 8.0, "screw_clear": 6.6, "min_boss_od": 12.5},
}


def insert_spec(key):
    """Look up an insert size, tolerant of case / stray spacing."""
    k = str(key).strip().upper().replace(" ", "")
    if k in ("2", "2.0"):
        k = "M2"
    elif k in ("2.5",):
        k = "M2.5"
    elif k in ("3", "3.0"):
        k = "M3"
    elif k in ("4", "4.0"):
        k = "M4"
    elif k in ("5", "5.0"):
        k = "M5"
    elif k in ("6", "6.0"):
        k = "M6"
    return INSERT_TABLE.get(k, INSERT_TABLE["M3"])


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "boss"))  # boss|boss_ribbed|boss_strip
if target_part not in ("boss", "boss_ribbed", "boss_strip"):
    target_part = "boss"

insert_size = str(PARAM(lambda: insert_size, "M3"))     # M2..M6
mount = str(PARAM(lambda: mount, "standalone"))         # standalone|in_wall
if mount not in ("standalone", "in_wall"):
    mount = "standalone"

boss_od = float(PARAM(lambda: boss_od, 0.0))            # 0 → auto (2.4× insert hole)
boss_height = float(PARAM(lambda: boss_height, 10.0))   # boss height above the base
through = bool(PARAM(lambda: through, False))           # through-bore vs blind
ribs = bool(PARAM(lambda: ribs, False))                # gusset ribs (boss/boss_ribbed)
rib_count = int(PARAM(lambda: rib_count, 4))            # number of gusset ribs
base_thick = float(PARAM(lambda: base_thick, 3.0))      # flange / wall thickness
base_margin = float(PARAM(lambda: base_margin, 5.0))    # flange material beyond the boss
strip_count = int(PARAM(lambda: strip_count, 3))        # bosses in a strip
strip_pitch = float(PARAM(lambda: strip_pitch, 25.0))   # centre-to-centre pitch

spec = insert_spec(insert_size)
insert_hole = spec["insert_hole"]

# Clamp to safe, watertight ranges.
boss_height = max(4.0, boss_height)
base_thick = max(1.5, base_thick)
base_margin = max(2.0, base_margin)
rib_count = max(2, min(rib_count, 8))
strip_count = max(2, min(strip_count, 10))

# Auto boss OD: ~2.4× the insert bore gives a robust wall, but honour the table
# minimum and any explicit override.
if boss_od <= 0.1:
    boss_od = max(spec["min_boss_od"], insert_hole * 2.4)
boss_od = max(insert_hole + 2.4, boss_od)   # never thinner than ~1.2 mm wall
boss_r = boss_od / 2.0

# Insert bore depth: heat-set inserts are ~ the screw diameter long; bore a little
# deeper than the insert so it seats fully. Blind bosses keep a floor.
bore_depth = boss_height if through else max(3.0, boss_height - max(1.5, base_thick * 0.5))
strip_pitch = max(boss_od + 2.0, strip_pitch)


# ── Helpers ──────────────────────────────────────────────────────────────────
def one_boss(with_ribs):
    """A single boss standing at the origin on z=0, rising +Z. Returns the boss
    cylinder (with its bore) plus optional ribs — NOT including the base."""
    boss = cq.Workplane("XY").circle(boss_r).extrude(boss_height)
    # Insert bore from the TOP.
    bore = (
        cq.Workplane("XY")
        .workplane(offset=boss_height)
        .circle(insert_hole / 2.0)
        .extrude(-bore_depth)
    )
    boss = boss.cut(bore)
    # Lead-in chamfer at the bore mouth eases starting the insert.
    try:
        boss = boss.edges(">Z").chamfer(min(0.6, (boss_r - insert_hole / 2.0) * 0.5))
    except Exception:
        pass

    if with_ribs:
        boss = boss.union(_ribs())
    return boss


def _ribs():
    """Triangular gusset ribs from the boss wall out to the base, evenly spaced."""
    rib_t = max(1.2, boss_od * 0.12)          # rib thickness
    rib_out = base_margin + boss_r * 0.4      # how far a rib reaches from centre
    rib_h = min(boss_height * 0.8, boss_height - 1.0)
    result = None
    for i in range(rib_count):
        # A right-triangle prism: tall at the boss, tapering to the base rim.
        tri = (
            cq.Workplane("XZ")
            .polyline([(boss_r - 0.5, 0.0), (rib_out, 0.0), (boss_r - 0.5, rib_h)])
            .close()
            .extrude(rib_t)
            .translate((0, rib_t / 2.0, 0))
        )
        tri = tri.rotate((0, 0, 0), (0, 0, 1), i * 360.0 / rib_count)
        result = tri if result is None else result.union(tri)
    return result


def base_flange():
    """A base to anchor the boss. `standalone` → a round flange with two mounting
    holes; `in_wall` → a rectangular wall/plate segment the boss sits on."""
    if mount == "in_wall":
        # A wall/plate segment: a slab the boss projects from.
        w = boss_od + 2.0 * base_margin + 8.0
        d = boss_od + 2.0 * base_margin
        slab = (
            cq.Workplane("XY")
            .box(w, d, base_thick, centered=(True, True, False))
        )
        return slab
    # Standalone round flange with two fixing holes to glue / screw it down.
    flange_r = boss_r + base_margin
    flange = cq.Workplane("XY").circle(flange_r).extrude(base_thick)
    fix_dia = min(4.0, insert_hole)
    hx = flange_r - max(fix_dia, 3.0)
    if hx > fix_dia:
        holes = (
            cq.Workplane("XY")
            .pushPoints([(-hx, 0.0), (hx, 0.0)])
            .circle(fix_dia / 2.0)
            .extrude(base_thick + 2.0)
            .translate((0, 0, -1.0))
        )
        flange = flange.cut(holes)
    return flange


def build_single(with_ribs):
    base = base_flange()
    boss = one_boss(with_ribs)
    # Boss overlaps the base by a hair for a watertight union.
    boss = boss.translate((0, 0, base_thick - min(0.6, base_thick * 0.4)))
    solid = base.union(boss)
    # If the boss is a through-bore, re-drill through the base so the hole is open.
    if through:
        drill = (
            cq.Workplane("XY")
            .circle(insert_hole / 2.0)
            .extrude(base_thick + boss_height + 2.0)
            .translate((0, 0, -1.0))
        )
        solid = solid.cut(drill)
    return solid


def build_strip():
    """A row of `strip_count` bosses on one common base bar at `strip_pitch`."""
    span = (strip_count - 1) * strip_pitch
    bar_w = span + boss_od + 2.0 * base_margin
    bar_d = boss_od + 2.0 * base_margin
    bar = (
        cq.Workplane("XY")
        .box(bar_w, bar_d, base_thick, centered=(True, True, False))
    )
    solid = bar
    x0 = -span / 2.0
    for i in range(strip_count):
        x = x0 + i * strip_pitch
        boss = one_boss(ribs)
        boss = boss.translate((x, 0, base_thick - min(0.6, base_thick * 0.4)))
        solid = solid.union(boss)
        if through:
            drill = (
                cq.Workplane("XY")
                .circle(insert_hole / 2.0)
                .extrude(base_thick + boss_height + 2.0)
                .translate((x, 0, -1.0))
            )
            solid = solid.cut(drill)
    return solid


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "boss_strip":
    result = build_strip()
elif target_part == "boss_ribbed":
    result = build_single(True)
else:
    result = build_single(ribs)
