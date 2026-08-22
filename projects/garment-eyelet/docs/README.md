# Garment Eyelet and Washer

A 3D-printed **two-part garment eyelet** — generated with **CadQuery** (B-Rep). A flanged
barrel passes through the fabric stack and is set against a plain, toothless washer on the
reverse. Fashion Cabinet's `garment-eyelet` notion owns the fashion semantics (hole
placement, lacing pitch, stack thickness) and bridges to **this** solid for the hardware.

This is a true garment finding. It is *not* the `desk-grommet` cartridge, which is an office
cable pass-through with a snap-fit lip and no sewn flange — garments should bridge here.

Part of the **Yantra4D Hyperobjects Commons**.
Official visualizer and configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Eyelet and Washer** | `set` | Both pieces laid out side by side, ready to print as a pair. |
| **Eyelet Only** | `eyelet` | The flange disc with the barrel tube rising from it, bored through. |
| **Washer Only** | `washer` | The plain annulus the barrel is set against. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Hole | `inner_dia` | 5.0 mm | Clear bore the lace or drawstring passes through. Range 3–12 mm. |
| Body | `flange_dia` | 10.0 mm | Face flange and washer outer diameter. Auto-raised to at least `inner_dia + 2*wall + 1`. |
| Body | `barrel_h` | 3.0 mm | Barrel height = compressed fabric stack plus roll allowance. |
| Body | `wall` | 1.2 mm | Barrel wall; barrel outer diameter is `inner_dia + 2*wall`. |
| Body | `washer_t` | 1.2 mm | Thickness of both the flange and the washer. |

All cross-parameter safety lives in `main.py` clamps, so no combination of slider values can
produce an invalid or non-manifold solid.

## Presets

- **Corset Lacing (#00)** — 4 mm bore, tall barrel for a doubled coutil panel.
- **Hoodie Drawstring** — 8 mm bore, wide flange for jersey.
- **Heavy Canvas** — 11 mm bore, thick flange and 6 mm stack.

## Print notes

Print the eyelet **flange-down** on the bed: the barrel then rises in free air with no
supports and the visible face comes out flat and clean. The washer prints flat either way.
PETG or recycled PETG holds a set better than PLA at garment scale; the barrel is thin, so
use at least three perimeters. For a permanent set, heat-flare the barrel crown over the
washer, or use a drop of adhesive between the two flat faces.

## Hyperobject Profile

- **Domain:** wearable
- **CDG interfaces:**
  - **Barrel** (`socket`, internal) — the fabric-stack passage, defined by `inner_dia`,
    `barrel_h`, `wall`.
  - **Set Face** (`flange`, internal) — the sewn/set flange; **this is the dimensional
    handshake surface** the Fashion Cabinet garment couples to, defined by `flange_dia`,
    `washer_t`.

## Fashion Cabinet bridge

FC-side `notion.hardware_ref` for the `garment-eyelet` notion:

```json
{
  "platform": "yantra4d",
  "project_slug": "garment-eyelet",
  "linked": true,
  "params_map": {
    "inner_dia": "eyelet_bore_mm",
    "flange_dia": "eyelet_bore_mm + 2 * eyelet_flange_margin_mm",
    "barrel_h": "fabric_stack_mm + 0.8",
    "wall": "eyelet_wall_mm",
    "washer_t": "eyelet_wall_mm"
  }
}
```

The garment drives the finding: the finished lace hole sets `inner_dia`, the compressed
seam-allowance stack (plus roll allowance) sets `barrel_h`, and the `set_face` flange is the
interface FC measures against the garment face. `CERN-OHL-W-2.0`.
