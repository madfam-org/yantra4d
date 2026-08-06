"""
Hitch Plug Holder — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Stows a trailer wiring connector when it isn't plugged in, so it doesn't drag on
the ground or corrode. Two dominant plug bodies are supported: the flat 4-pin
connector and the round 7-pin connector (SAE J1128 family). Three modes:

  * "plug_holder"  — a pocket that cradles the plug body, on a bracket that bolts
                     to the hitch or bumper — the plug's parking spot.
  * "dust_cap"     — a cap that plugs onto/into the connector to keep dirt and
                     water out of the pins.
  * "socket_mount" — a panel/bracket mount that holds the vehicle-side socket at
                     a fixed spot (e.g. on the bumper or a plate).

The plug-body socket is the Common Denominator Geometry — sized to the chosen
plug so every mode presents the same interface envelope.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `plug`).
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


# ── Plug standard table ──────────────────────────────────────────────────────
# SAE J1128 family. The 4-pin flat connector has a flat rectangular body; the
# 7-pin round connector has a cylindrical body. Dimensions are the nominal body
# envelope (mm) the holder cups, plus a printable seating clearance.
#   shape: "flat" (rect body: bw × bh) or "round" (dia).
PLUG_TABLE = {
    "4pin": {"shape": "flat", "bw": 24.0, "bh": 10.0, "depth": 22.0},
    "7pin": {"shape": "round", "dia": 44.0, "depth": 28.0},
}


def plug_spec(key):
    """Look up a plug type, tolerant of case / spacing / aliases."""
    k = str(key).strip().lower().replace(" ", "").replace("-", "")
    if k in ("4pinflat", "4pin", "4flat", "flat4", "flat"):
        k = "4pin"
    elif k in ("7pinround", "7pin", "7round", "round7", "round"):
        k = "7pin"
    return PLUG_TABLE.get(k, PLUG_TABLE["4pin"])


# ── Parameters ───────────────────────────────────────────────────────────────
plug         = str(  PARAM(lambda: plug,        "4-pin flat"))  # "4-pin flat" | "7-pin round"
wall         = float(PARAM(lambda: wall,          3.0))   # holder/cap wall thickness
clearance    = float(PARAM(lambda: clearance,     0.6))   # per-side fit clearance around the plug
socket_depth = float(PARAM(lambda: socket_depth,  0.0))   # cup depth (0 = auto from plug)
bracket_h    = float(PARAM(lambda: bracket_h,    34.0))   # bracket height (plug_holder / socket_mount)
bolt_dia     = float(PARAM(lambda: bolt_dia,      6.5))   # mounting bolt clearance hole (M6)
tether_hole  = bool( PARAM(lambda: tether_hole,  True))   # add a lanyard/tether hole (dust_cap)

target_part  = str(  PARAM(lambda: target_part, "plug_holder"))
# "plug_holder" | "dust_cap" | "socket_mount"


# ── Derived / clamped geometry ───────────────────────────────────────────────
spec = plug_spec(plug)
wall = max(1.6, wall)
clearance = max(0.0, clearance)
is_round = spec["shape"] == "round"
depth = spec["depth"] if socket_depth <= 0.0 else max(6.0, socket_depth)

if is_round:
    body_r = spec["dia"] / 2.0 + clearance
    outer_r = body_r + wall
    # Bounding footprint for brackets.
    foot_w = 2.0 * outer_r
    foot_h = 2.0 * outer_r
else:
    bw = spec["bw"] + 2.0 * clearance
    bh = spec["bh"] + 2.0 * clearance
    foot_w = bw + 2.0 * wall
    foot_h = bh + 2.0 * wall


# ── Shared helpers ────────────────────────────────────────────────────────────
def plug_cup(cup_depth, floor=None):
    """A cup that cradles the plug body: an outer shell (round or rectangular)
    hollowed to the plug envelope from the +Z face, on a floor of thickness
    `floor`. Base at z=0, open at the top. Watertight."""
    fl = wall if floor is None else max(1.2, floor)
    if is_round:
        outer = (
            cq.Workplane("XY")
            .circle(outer_r)
            .extrude(cup_depth + fl)
        )
        bore = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, fl))
            .circle(body_r)
            .extrude(cup_depth + 1.0)
        )
    else:
        outer = (
            cq.Workplane("XY")
            .box(foot_w, foot_h, cup_depth + fl, centered=(True, True, False))
        )
        try:
            outer = outer.edges("|Z").fillet(min(2.5, wall))
        except Exception:
            pass
        bore = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, fl))
            .box(bw, bh, cup_depth + 1.0, centered=(True, True, False))
        )
    return outer.cut(bore)


def bolt_bracket(height):
    """A flat bracket wall behind the cup with two mounting bolt holes, for
    bolting to the hitch/bumper. Stands in the −Y plane, base at z=0. The plate
    overlaps a couple of mm into the cup body so the union is a solid merge (not
    a tangency that would leave a non-manifold edge)."""
    bw_plate = max(foot_w, 2.0 * bolt_dia + 16.0)
    overlap = 2.0
    plate_t = wall + overlap
    # Centre so the plate's front face reaches `overlap` into the cup footprint.
    plate_yc = -foot_h / 2.0 - wall / 2.0 + overlap
    plate = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, plate_yc, 0))
        .box(bw_plate, plate_t, height, centered=(True, True, False))
    )
    try:
        plate = plate.edges("|Y").fillet(min(3.0, wall))
    except Exception:
        pass
    # Two bolt holes through the plate (Y axis). Bore overshoots both faces.
    r = max(0.5, bolt_dia / 2.0)
    hx = bw_plate / 2.0 - max(r + 3.0, 6.0)
    hz = height - max(r + 3.0, 6.0)
    for sx in (-hx, hx):
        hole = (
            cq.Workplane("XZ")
            .transformed(offset=cq.Vector(sx, hz, plate_yc - plate_t / 2.0 - 1.0))
            .circle(r)
            .extrude(plate_t + 2.0)
        )
        plate = plate.cut(hole)
    return plate


# ── plug_holder ───────────────────────────────────────────────────────────────
def build_plug_holder():
    """A downward-opening cup on a bolt bracket: the plug parks nose-down so
    water drains out. Cup is built opening up then flipped onto the bracket."""
    cup = plug_cup(depth)
    bracket = bolt_bracket(max(bracket_h, depth + 6.0))
    return cup.union(bracket)


# ── dust_cap ──────────────────────────────────────────────────────────────────
def build_dust_cap():
    """A cap that covers the connector face: a shallow cup sized to slip over the
    plug body, with an optional tether hole in a small tab."""
    cap_depth = max(6.0, depth * 0.45)
    cap = plug_cup(cap_depth, floor=wall)

    if tether_hole:
        # Small side tab with a lanyard hole.
        tab = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(foot_w / 2.0 + 3.0, 0, 0))
            .box(10.0, min(foot_h, 14.0), wall, centered=(True, True, False))
        )
        cap = cap.union(tab)
        hole = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(foot_w / 2.0 + 6.0, 0, -1.0))
            .circle(2.2)
            .extrude(wall + 2.0)
        )
        cap = cap.cut(hole)
    return cap


# ── socket_mount ──────────────────────────────────────────────────────────────
def build_socket_mount():
    """A bracket that holds the vehicle-side socket at a fixed spot: a through
    pass-hole for the socket body on a bolt-down plate (flat panel mount)."""
    plate_t = wall + 2.0
    plate = (
        cq.Workplane("XY")
        .box(foot_w + 20.0, foot_h + 12.0, plate_t, centered=(True, True, False))
    )
    try:
        plate = plate.edges("|Z").fillet(min(4.0, (foot_h + 12.0) / 4.0))
    except Exception:
        pass

    # Central pass-through for the socket body.
    if is_round:
        pass_hole = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, -1.0))
            .circle(body_r)
            .extrude(plate_t + 2.0)
        )
    else:
        pass_hole = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, -1.0))
            .box(bw, bh, plate_t + 2.0, centered=(True, True, False))
        )
    plate = plate.cut(pass_hole)

    # Four corner bolt holes.
    r = max(0.5, bolt_dia / 2.0)
    hx = (foot_w + 20.0) / 2.0 - max(r + 3.0, 6.0)
    hy = (foot_h + 12.0) / 2.0 - max(r + 3.0, 6.0)
    for sx in (-hx, hx):
        for sy in (-hy, hy):
            hole = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(sx, sy, -1.0))
                .circle(r)
                .extrude(plate_t + 2.0)
            )
            plate = plate.cut(hole)

    # A short collar around the pass-hole to grip the socket.
    if is_round:
        collar = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, plate_t))
            .circle(outer_r)
            .extrude(max(6.0, depth * 0.4))
        )
        collar_bore = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, plate_t - 1.0))
            .circle(body_r)
            .extrude(depth)
        )
        plate = plate.union(collar.cut(collar_bore))
    return plate


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "dust_cap":
    result = build_dust_cap()
elif target_part == "socket_mount":
    result = build_socket_mount()
else:  # "plug_holder"
    result = build_plug_holder()
