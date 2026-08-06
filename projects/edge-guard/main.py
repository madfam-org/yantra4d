"""
Edge Guard — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Child-safety corner and edge guards that clip onto the edge of a table, counter, or shelf
to cushion sharp corners and edges. Each guard is a C-clip that grips the edge thickness
with a rounded outer cushion presented to the room. Sized by the edge thickness so it
snaps onto whatever furniture is in the home.

This is catalog object #200 — the capstone that closes the Open Commons of Hyperobjects.

Three parts (dispatched via `target_part`):
  * "corner_guard"   — an L-shaped corner cap: two clip channels meeting at 90° with a
                       rounded corner bumper, for the pointed corner of a table.
  * "edge_strip"     — a straight run of edge guard (a clip channel + rounded cushion) to
                       cover a long edge; sold by the length.
  * "cushion_bumper" — a stick-on rounded bumper pad (no clip) for a flat face or an edge
                       too thick to clip, held by adhesive.

The clip PROFILE is the shared CDG: a C-channel of opening `edge_t` + `fit`, gripping
depth `grip`, that hugs the furniture edge (refs `edge_t`). All prismatic — fast and
watertight; the rounded cushion is a filleted outer face.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `edge_t`).
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
target_part = str(PARAM(lambda: target_part, "corner_guard"))  # corner_guard|edge_strip|cushion_bumper

edge_t     = float(PARAM(lambda: edge_t,     22.0))   # furniture edge thickness (mm)
grip       = float(PARAM(lambda: grip,       18.0))   # how far the clip grips onto the face (mm)
cushion    = float(PARAM(lambda: cushion,    10.0))   # rounded cushion thickness in front of the edge (mm)
wall       = float(PARAM(lambda: wall,        3.0))   # guard wall thickness (mm)
fit        = float(PARAM(lambda: fit,         0.4))   # clip clearance so it slips on (mm)
length     = float(PARAM(lambda: length,    120.0))   # edge-strip length / corner arm length (mm)
corner_arm = float(PARAM(lambda: corner_arm, 55.0))   # corner-guard arm length per side (mm)

# Clamp inputs to sane ranges so extreme UI values still build watertight.
edge_t     = max(6.0, min(edge_t, 60.0))
grip       = max(8.0, min(grip, 50.0))
cushion    = max(4.0, min(cushion, 30.0))
wall       = max(2.0, min(wall, 8.0))
fit        = max(0.1, min(fit, 1.2))
length     = max(40.0, min(length, 300.0))
corner_arm = max(30.0, min(corner_arm, 120.0))

slot = edge_t + fit                    # clip opening (grips the edge)
outer_t = slot + 2.0 * wall + cushion  # total front-to-back depth of the guard body


# ── Clip cross-section (a C-channel + rounded cushion), extruded along a run ──
def _guard_section(run):
    """One straight run of edge guard of length `run` (extruded along +Y). Section (in the
    XZ plane, X across the edge, Z along the grip depth) is a C-channel: the furniture edge
    slides into a `slot`-wide × `grip`-deep pocket, walled on the back and both grip legs,
    with a rounded cushion block in front. Built solid then the pocket is cut; the front
    outer vertical edges are filleted into a soft cushion. Returns a solid centred in Y."""
    body_x = slot + 2.0 * wall + cushion   # total across-edge depth (== outer_t)
    body_z = grip + wall                    # total grip-leg length
    block = cq.Workplane("XY").box(body_x, run, body_z, centered=(True, True, False))
    # Pocket the furniture edge slides into: open toward -X (the room-facing cushion is +X).
    # The slot spans the middle `slot` across X, `grip` deep from the open (-X? ) end.
    pocket = (
        cq.Workplane("XY")
        .box(slot, run + 2.0, grip, centered=(True, True, False))
        .translate((-body_x / 2.0 + wall + slot / 2.0, 0, wall))
    )
    body = block.cut(pocket)
    # Round the front (+X) outer edges into a soft cushion.
    try:
        body = body.edges("|Y and >X").fillet(min(cushion * 0.9, body_z * 0.45))
    except Exception:
        pass
    # Soften the two open leg tips so they slide on and aren't sharp themselves.
    try:
        body = body.edges("|Y and <X").fillet(min(wall * 0.6, 1.5))
    except Exception:
        pass
    return body


# ── Part builders ─────────────────────────────────────────────────────────────
def build_edge_strip():
    """A straight run of edge guard covering a long edge (length `length`)."""
    return _guard_section(length)


def build_corner_guard():
    """An L-shaped corner cap: two clip runs meeting at 90° with a rounded corner. The two
    arms overlap at the corner so the union is one watertight body; the outer corner is
    rounded into a bump for the pointed table corner."""
    arm = corner_arm
    run_y = _guard_section(arm).translate((0, arm / 2.0, 0))          # arm along +Y
    run_x = (
        _guard_section(arm)
        .rotate((0, 0, 0), (0, 0, 1), 90.0)
        .translate((arm / 2.0, 0, 0))                                  # arm along +X
    )
    corner = run_y.union(run_x)
    # A rounded corner filler block at the join so the pointed corner is fully cushioned.
    fill = (
        cq.Workplane("XY")
        .box(outer_t, outer_t, grip + wall, centered=(True, True, False))
        .translate((0, 0, 0))
    )
    try:
        fill = fill.edges("|Z").fillet(min(outer_t * 0.45, cushion))
    except Exception:
        pass
    body = corner.union(fill)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_cushion_bumper():
    """A stick-on rounded bumper pad (no clip): a domed pad with a flat adhesive back for a
    flat face or an edge too thick to clip. A rounded box, flat on the mounting side."""
    pad_w = max(edge_t + 2.0 * cushion, 30.0)
    pad_l = length * 0.5
    pad_h = cushion + wall
    pad = cq.Workplane("XY").box(pad_w, pad_l, pad_h, centered=(True, True, False))
    # Round every top edge into a soft dome; keep the base (z=0) flat for adhesive.
    try:
        pad = pad.edges("|Z").fillet(min(pad_w * 0.3, pad_l * 0.3, cushion))
    except Exception:
        pass
    try:
        pad = pad.edges(">Z").fillet(min(cushion * 0.8, pad_h * 0.45))
    except Exception:
        pass
    return pad


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "edge_strip":
    result = build_edge_strip()
elif target_part == "cushion_bumper":
    result = build_cushion_bumper()
else:
    result = build_corner_guard()
