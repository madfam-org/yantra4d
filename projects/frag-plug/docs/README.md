# Aquarium Frag / Coral Plug

Coral propagation hardware for a reef tank, generated with **CadQuery** (B-Rep):
a mushroom-shaped frag plug whose stem pushes into a rack, a rack that stands a
grid of plugs on the sand bed, and a stemless gluing disc for mounting frags
straight onto live rock. Sized by the 25 mm disc / 6 mm stem reef-hobby
convention.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

> Print in **aquarium-safe filament** (uncoloured PETG is a common choice) and
> cure/rinse before adding to a reef tank.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Frag Plug** | `frag_plug` | The classic mushroom/nail plug — a round top disc on a tapered push-in stem, with a glue dimple. |
| **Frag Rack** | `frag_rack` | A solid bar on feet with a grid of stem holes bored through, to stand plugs upright on the sand bed. |
| **Gluing Disc** | `frag_disc` | A stemless disc with a domed top and an epoxy grip groove, for gluing a frag directly to rock. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Plug | `disc_dia` | 25.0 mm | Top disc diameter (standard 25 mm; mini 15–18, large 35–40). |
| Plug | `disc_h` | 4.0 mm | Disc thickness. |
| Plug | `stem_dia` | 6.0 mm | Stem diameter (typical 6 mm; heavy 8–10). |
| Plug | `stem_h` | 18.0 mm | Push-in stem length below the disc. |
| Rack | `hole_dia` | 6.4 mm | Rack hole diameter (clears a 6 mm stem). |
| Rack | `rack_cols` | 4 | Plug holes per row. |
| Rack | `rack_rows` | 2 | Rows of plug holes. |
| Rack | `rack_pitch` | 22.0 mm | Center-to-center hole spacing. |

## Presets

- **Standard Plug (25/6 mm)** — the reef-hobby default.
- **8-Up Frag Rack** — a 4×2 grid on feet.
- **Gluing Disc (25 mm)** — stemless, for rock.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Plug Stem / Rack Socket** (`socket`, internal) — the plug stem and the
    matching rack hole, defined by `stem_dia`, `stem_h`, `hole_dia`. Match the
    hole to the stem (add ~0.4 mm) and every plug in a system shares one stem
    diameter.
- **Material awareness:** `tolerance_by_material` is declared — a slightly
  flexible material grips the rack hole with less clearance.
- **Societal benefit:** propagates coral sustainably, reducing wild harvest, and
  lets a reefer or frag-swap club standardise on one stem diameter for cents
  apiece instead of bulk packs sized to no particular tank.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via `PARAM(lambda: name, default)`;
  final solid assigned to `result`.
- Watertight strategy: the plug is a solid disc unioned to a tapered `makeCone`
  stem (overlapping into shared material), filleted before the glue dimple is
  cut; the rack bores stem holes fully through the top face; the disc is a solid
  puck. All openings vent to a face — no trapped voids.
- All shipped presets and defaults render **watertight**, single-body.
