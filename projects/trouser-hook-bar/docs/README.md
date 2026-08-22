# Trouser Hook & Bar

The heavy waistband closure of tailored trousers, pencil skirts and culottes —
generated with **CadQuery** (B-Rep). A flat hook plate whose tongue folds back on
itself, and a flat bar plate carrying a raised bridge the tongue drops behind.

This is a different animal from [`hook-and-eye`](../../hook-and-eye), which is the
bra-weight sprung hook. This one is wider, thicker and sewn flat *inside* a
waistband so the closure carries real load without showing through the face cloth.
Naming is deliberately shared with that cartridge (`plate_t`, `wire_d`, `gap`) so a
garment can drive either from the same fields.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part(s) | Description |
| :--- | :--- | :--- |
| **Hook & Bar Set** | `hook_plate`, `bar_plate` | Both plates laid side by side, as sewn on a waistband. |
| **Hook Plate** | `hook_plate` | The tongue side, sewn to the waistband overlap. |
| **Bar Plate** | `bar_plate` | The catch side, sewn to the waistband underlap. |

## Parameters

| Group | Parameter | Default | Range | Notes |
| :--- | :--- | :--- | :--- | :--- |
| Plate | `hook_width` | 10.0 mm | 6–20 | Plate width across the band. Keep under the finished waistband height. |
| Plate | `plate_len` | 14.0 mm | 8–25 | Plate length along the band, sewing end to catch end. |
| Plate | `plate_t` | 1.6 mm | 1.2–3.0 | Plate thickness. Thicker resists a heavy band but shows through more. |
| Plate | `sew_holes` | 4 | 2–8 | Stitch holes per plate; auto-reduced if they would not fit. |
| Closure | `wire_d` | 1.6 mm | 1.0–3.0 | Stock diameter of the folded tongue and the crossbar. |
| Print Fit | `gap` | 0.35 mm | 0.2–0.8 | Hook-to-bar clearance. |

The hook mouth opening is held at exactly **`wire_d + gap`** for every combination,
so the printed bar always clears the printed tongue. `wire_d` is additionally
clamped against `hook_width` and `plate_len` so slim plates cannot grow oversized
stock, and features standing on a plate are kept clear of its corner fillets. On
small or narrow plates the corner fillet shrinks automatically, and squares off
entirely once it would fall below 0.4 mm, to keep a flat core wide enough to carry
the tongue and the bridge posts.

## Presets

- **Suit Trouser Waistband** — the 10 × 14 mm default.
- **Pencil Skirt (slim band)** — 7.5 × 11 mm for a narrow band.
- **Heavy Culottes (wide band)** — 16 × 20 mm, thicker stock.

## Print notes

Print both plates **flat on the bed, plate face down** — the tongue's fold-back arc
and the bar bridge then print as clean upward arches needing little or no support.
Use a stiff material: PETG or PA (nylon) hold the spring of the tongue far better
than PLA, which creeps under a waistband's sustained load. Recycled and offcut
material is fine for these (`recycled_material_toggle` in the profile). If the hook
slips off in wear, reduce `gap`; if it will not seat, raise it 0.05 mm at a time.

## Hyperobject Profile

- **Domain:** wearable
- **CDG interfaces:**
  - **Sewing Plate** (`flange`, internal) — the sewn/set flange, defined by
    `hook_width`, `plate_t`, `sew_holes`. **This is the dimensional-handshake
    interface** Fashion Cabinet matches against the waistband.
  - **Hook / Bar Catch** (`snap`, internal) — the engaging pair, defined by
    `wire_d`, `gap`.

## Fashion Cabinet bridge

FC owns the waistband and placement math; this cartridge owns the hardware solid.
The garment notion references it with:

```json
{
  "hardware_ref": {
    "platform": "yantra4d",
    "project_slug": "trouser-hook-bar",
    "linked": true,
    "params_map": {
      "hook_width": "waistband_height_mm * 0.6",
      "plate_len": "waistband_height_mm * 0.85",
      "plate_t": "closure_weight == 'heavy' ? 2.4 : 1.6",
      "wire_d": "closure_weight == 'heavy' ? 2.4 : 1.6",
      "sew_holes": "4",
      "gap": "0.35"
    }
  }
}
```

The handshake runs through the **`sew_plate`** flange interface: FC sizes the plate
from the garment's finished waistband height so the hardware disappears inside the
band, and y4d returns the solid that fits it.
