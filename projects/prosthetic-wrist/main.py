import cadquery as cq
import math


# ─── Sandbox-safe parameter access ───────────────────────────────────────────
def PARAM(getter, default):
    try:
        return getter()
    except Exception:
        return default


target_part = PARAM(lambda: target_part, "wrist_plate")
plate_dia = float(PARAM(lambda: plate_dia, 58.0))
bolt_circle_dia = float(PARAM(lambda: bolt_circle_dia, 40.0))
bolt_dia = float(PARAM(lambda: bolt_dia, 5.5))
plate_th = float(PARAM(lambda: plate_th, 8.0))
disc_dia = float(PARAM(lambda: disc_dia, 22.0))
flex_angle = float(PARAM(lambda: flex_angle, 20.0))

# ─── Real-world reference dimensions (cited in manifest CDG standards) ─────────
# e-NABLE / Open Source Leg 4-bolt terminal interface: four bolts on a square
#   pattern on a ~40 mm bolt circle, M5 (5.5 mm clearance) — the same distal
#   adapter the `prosthetic-socket` cartridge exposes, so a limb, wrist and
#   terminal device all interoperate. The central boss is a keyed quick-disconnect.
KEY_FLAT = 0.72   # fraction of disc radius kept as the D-flat (anti-rotation key)


def _fillet_safe(wp, sel, r):
    try:
        return wp.edges(sel).fillet(r)
    except Exception:
        return wp


def _bolt_points(bcd, n=4):
    """N bolt centres on the bolt circle (square pattern for n=4), starting at 45°
    so the four holes sit at the diagonals like the e-NABLE terminal."""
    r = bcd / 2.0
    pts = []
    for i in range(n):
        a = math.radians(45.0 + 360.0 * i / n)
        pts.append((r * math.cos(a), r * math.sin(a)))
    return pts


def _four_bolt_plate(diameter, thickness, bcd, hole_d, fillet_top=True):
    """A round flange with the 4-bolt through pattern. Filleted BEFORE the holes
    are cut (filleting a hole-laden solid crashes OCCT clean())."""
    plate = cq.Workplane("XY").circle(diameter / 2.0).extrude(thickness)
    if fillet_top:
        plate = _fillet_safe(plate, "|Z", 1.2)
    holes = (
        cq.Workplane("XY")
        .pushPoints(_bolt_points(bcd))
        .circle(hole_d / 2.0)
        .extrude(thickness + 2.0)
        .translate((0, 0, -1.0))
    )
    return plate.cut(holes)


def _key_socket(depth, disc_d):
    """A cutter shaped like the keyed quick-disconnect: a cylinder with one flat
    (a D-profile) so the terminal puck cannot rotate once seated."""
    r = disc_d / 2.0
    cyl = (
        cq.Workplane("XY")
        .circle(r)
        .extrude(depth)
    )
    # Slice off a chord to make the D-flat.
    flat = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, r * KEY_FLAT + r, 0))
        .box(r * 4.0, r * 2.0, depth + 2.0, centered=(True, True, False))
        .translate((0, 0, -1.0))
    )
    return cyl.cut(flat)


def _key_post(height, disc_d, clearance=0.35):
    """The matching keyed post (D-profile), sized under the socket by clearance."""
    r = disc_d / 2.0 - clearance
    cyl = cq.Workplane("XY").circle(r).extrude(height)
    flat = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, r * KEY_FLAT + r + clearance, 0))
        .box(r * 4.0, r * 2.0, height + 2.0, centered=(True, True, False))
        .translate((0, 0, -1.0))
    )
    return cyl.cut(flat)


# ─── Mode 1: wrist plate (4-bolt flange + keyed quick-disconnect socket) ───────
def build_wrist_plate():
    """A round flange that bolts to the socket's distal 4-bolt (e-NABLE/OSL)
    adapter and presents a keyed quick-disconnect SOCKET on its outer face so a
    terminal device puck drops in and locks against rotation. The socket is a
    blind pocket opening to the top face; the bolt holes pass through — all open
    to a face, no trapped void."""
    total_th = plate_th + max(6.0, disc_dia * 0.5)
    plate = _four_bolt_plate(plate_dia, total_th, bolt_circle_dia, bolt_dia)

    # Keyed socket pocket from the top face, not reaching the bolt-flange floor.
    sock_depth = total_th - plate_th
    socket = _key_socket(sock_depth + 1.0, disc_dia + 0.7).translate(
        (0, 0, total_th - sock_depth))
    plate = plate.cut(socket)
    return plate


# ─── Mode 2: terminal puck (mating quick-disconnect coupler) ──────────────────
def build_terminal_puck():
    """The mating quick-disconnect coupler: a base flange with its OWN 4-bolt
    pattern (to bolt a terminal device / hand to it) and a keyed post that seats
    into the wrist-plate socket. Solid post on an open-faced flange → watertight."""
    base_th = max(6.0, plate_th * 0.7)
    post_h = max(6.0, disc_dia * 0.5)
    flange_d = max(disc_dia + 14.0, bolt_circle_dia + bolt_dia + 8.0)

    base = _four_bolt_plate(flange_d, base_th, bolt_circle_dia, bolt_dia, fillet_top=False)

    post = _key_post(post_h, disc_dia).translate((0, 0, base_th))
    puck = base.union(post)
    puck = _fillet_safe(puck, ">Z", 0.8)
    return puck


# ─── Mode 3: fixed-flexion wrist block ────────────────────────────────────────
def build_wrist_flexion():
    """Two 4-bolt flanges joined by a solid wedge so the terminal device sits at a
    fixed wrist flexion angle relative to the socket. Proximal flange bolts to the
    socket; distal flange carries the terminal device. Both bolt patterns pass
    through their own flange into open air; the connecting wedge is solid."""
    fl_d = max(plate_dia, bolt_circle_dia + bolt_dia + 10.0)
    fl_th = max(6.0, plate_th * 0.8)
    ang = max(0.0, min(45.0, flex_angle))

    # Proximal flange in the XY plane at z=0.
    prox = _four_bolt_plate(fl_d, fl_th, bolt_circle_dia, bolt_dia, fillet_top=False)

    # A solid central column that carries the load between the two flanges. Its
    # top is domed enough that a tilted distal flange always overlaps it.
    col_r = fl_d / 2.0 - 3.0
    col_h = fl_d * 0.55
    column = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, fl_th))
        .circle(col_r)
        .extrude(col_h)
    )
    col_top = fl_th + col_h
    body = prox.union(column)

    # Distal flange: build it centred on the origin so it rotates about its own
    # centre, tilt by the flexion angle, then seat it so the SOLID column clearly
    # passes THROUGH the flange (a deep, unambiguous overlap — not a near-tangent
    # kiss). A tangent union at 45° produces coincident tessellation faces that
    # split the STL mesh into components even though the BREP is one solid; a deep
    # overlap tessellates as one connected body.
    distal = _four_bolt_plate(fl_d, fl_th, bolt_circle_dia, bolt_dia, fillet_top=False)
    distal = distal.translate((0, 0, -fl_th / 2.0))          # centre on Z=0
    distal = distal.rotate((0, 0, 0), (1, 0, 0), ang)         # tilt about centre
    # Seat the flange centre a full thickness below the column top so the column
    # cross-section fully engulfs the flange's mid-region at every tilt 0..45°.
    seat_z = col_top - fl_th
    distal = distal.translate((0, 0, seat_z))
    body = body.union(distal)

    body = _fillet_safe(body, "|Z", 1.0)
    return body


# ─── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "wrist_plate":
    result = build_wrist_plate()
elif target_part == "terminal_puck":
    result = build_terminal_puck()
elif target_part == "wrist_flexion":
    result = build_wrist_flexion()
else:
    result = build_wrist_plate()
