# Arca-to-GoPro Adapter

A cross-family **bridge** between the tripod world (**Arca-Swiss** 38 mm
dovetail) and the action-cam world (**GoPro** finger clevis), generated with
**CadQuery** (B-Rep). One face is a 38 mm Arca dovetail that drops into any Arca
clamp; the other is a GoPro finger bank (2-prong female or 3-prong male) that
mates any GoPro accessory. So an Arca tripod head can carry a GoPro chain, or a
GoPro cage can bolt to an Arca plate.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Arca → GoPro (2-prong)** | `arca_to_gopro` | Arca dovetail plate (platform down) with a GoPro **2-prong female** finger bank rising from the top. |
| **Arca → GoPro (3-prong)** | `gopro_to_arca` | Arca dovetail plate with a GoPro **3-prong male** finger bank — nests inside a 2-prong accessory. |
| **Low-Profile Bridge** | `arca_gopro_flat` | A compact filleted puck with GoPro 3-prong fingers on a short Arca dovetail — sits lower than the full plate. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Arca Dovetail | `plate_w` | 38.0 mm | Dovetail platform width (Arca standard). |
| Arca Dovetail | `flank_ang` | 45° | Dovetail flank undercut angle from vertical. |
| Arca Dovetail | `plate_h` | 9.0 mm | Arca dovetail block height. |
| Arca Dovetail | `plate_len` | 46.0 mm | Base length along Y. |
| GoPro Fingers | `finger_thick` | 3.0 mm | GoPro finger thickness (standard ~3 mm). |
| GoPro Fingers | `finger_gap` | 3.2 mm | Gap between fingers; a mating finger nests here. |
| GoPro Fingers | `knuckle_d` | 15.0 mm | Knuckle diameter (standard ~15 mm). |
| GoPro Fingers | `bolt_hole_d` | 5.0 mm | M5 thumbscrew axle through-hole. |
| GoPro Fingers | `reach` | 16.0 mm | Knuckle pivot height above the base top. |

## Two standards, one part

The **Arca side** is a 38 mm dovetail — wider at the bottom because the flanks
undercut at `flank_ang` (bottom width `plate_w + 2·plate_h·tan(flank_ang)`), so
an Arca clamp jaw wedges it down and centres it. The **GoPro side** is the finger
clevis: fingers of thickness `finger_thick` on a pitch of
`finger_thick + finger_gap` (~6.2 mm) so a mating prong's finger drops into each
gap, then an M5 thumbscrew runs through the aligned `bolt_hole_d` knuckle holes.
The fingers' shafts overlap down into the dovetail's flat top with real material,
so the whole bridge is one watertight body; the axle hole vents to outside.

## Presets

- **Arca Head → GoPro Cage** — 2-prong female for hanging a GoPro cage.
- **Arca Head → GoPro Mount (male)** — 3-prong male to nest into an accessory.
- **Low-Profile Bridge** — a short, low bridge for minimal stack height.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **Arca-Swiss Dovetail** (`profile`, *Arca-Swiss 38mm*) — defined by `plate_w`,
    `flank_ang`, `plate_h`. **Mates:** [`arca-plate`](../../arca-plate/) (its
    clamp and QR plate grip this dovetail).
  - **GoPro Finger Clevis** (`snap`, *GoPro action-cam mount*) — defined by
    `finger_thick`, `finger_gap`, `knuckle_d`, `bolt_hole_d`. **Mates:**
    [`gopro-mount`](../../gopro-mount/) (its 2-prong / 3-prong banks interleave
    with this one).
- **Material awareness:** `tolerance_by_material` is declared — the finger gap
  and dovetail dimensions are exposed so both fits tune per material/printer.
- **Societal benefit:** the Arca dovetail and the GoPro finger mount are two of
  the most widespread open camera interfaces but never meet without a proprietary
  adapter. This bridge is that adapter — a shared node touching both families so
  the whole Arca and GoPro accessory ecosystems interoperate.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via a `PARAM(lambda: name, default)`
  guard; `target_part` dispatches the part; the final solid is `result`.
- The Arca base is an extruded dovetail cross-section; GoPro fingers are
  knuckle-cylinder + shaft-box unions overlapping into the base top; the axle
  hole is a through-cut (vented). All shipped modes and extreme-parameter cases
  render **watertight**, single-body, in well under 30 s.
