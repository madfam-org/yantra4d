# Lacing Hook

The printable **speed hook** — the upturned horn a lace is zig-zagged over on a
corset, a bodice, or a boot-style closure. Generated with **CadQuery** (B-Rep).
Fashion Cabinet's `lacing-hook` notion owns the fashion semantics (lacing-edge
placement, cord path, hook count along the opening) and bridges to **this** solid
for the hardware. It pairs with [`garment-eyelet`](../../garment-eyelet/) on the
opposing edge: eyelets below, speed hooks above, the classic heritage /
footwear-adjacent lacing.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Hook Row** | `set` | A row of `hook_count` hooks on a shared centreline, spaced by `pitch` — print the whole lacing edge in one go. |
| **Single Hook** | `hook` | One hook, for repairs and for setting hooks at irregular spacing. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Row | `hook_count` | 4 | Hooks generated in `set` mode (2–8). |
| Row | `pitch` | 12.0 mm | Centre-to-centre hook spacing; never allowed below `plate_w + 1`. |
| Horn | `cord_dia` | 4.0 mm | Lace/cord diameter. The horn mouth opens at `cord_dia + 0.5`. |
| Plate | `plate_w` | 9.0 mm | Base plate width across the lacing edge. |
| Plate | `plate_t` | 1.6 mm | Plate thickness; also sets the horn stock gauge. |
| Plate | `rivet_hole_dia` | 2.5 mm | Setting hole for the rivet/tack; capped at `0.45 × plate_w`. |

## Presets

- **Corset Lacing Row** — 6 hooks, 3 mm cord, 14 mm pitch.
- **Boot Speed Hook** — a single heavier hook for 5 mm boot lace.

## Hyperobject Profile

- **Domain:** wearable
- **CDG interfaces:**
  - **Sew / Rivet Plate** (`sew_plate`, `flange`, internal) — the set edge that
    meets the garment, defined by `plate_w`, `plate_t`, `rivet_hole_dia`. **This
    is the flange for the FC dimensional handshake.**
  - **Cord Catch** (`cord_catch`, `snap`, internal) — the horn mouth and the row
    rhythm the cord runs through, defined by `cord_dia`, `pitch`.

## Fashion Cabinet bridge

Suggested FC-side `hardware_ref` on the `lacing-hook` notion:

```json
{
  "platform": "yantra4d",
  "project_slug": "lacing-hook",
  "linked": true,
  "params_map": {
    "cord_dia": "lace_cord_mm",
    "pitch": "lacing_edge_length_mm / (lacing_hook_count - 1)",
    "hook_count": "lacing_hook_count",
    "plate_w": "facing_width_mm * 0.6",
    "plate_t": "shell_thickness_mm + interlining_mm",
    "rivet_hole_dia": "setting_tack_mm"
  }
}
```

The dimensional handshake runs through `sew_plate`: FC's finished facing width
and shell/interlining stack drive `plate_w` and `plate_t`, so the hook's set edge
always matches the garment layer it is riveted through.

## Fabrication notes

Print **plate-down** so the horn grows upward and the curl self-supports; no
supports are needed at the default gauge. Every mode exports a watertight solid —
the `set` mode returns `hook_count` separate watertight bodies on one build plate.
The rivet hole is cut clear through both faces. Rigid material (PETG, PLA+, or a
recycled/offcut filament — see `recycled_material_toggle` in the profile) at high
infill; nylon or PETG if the lacing takes real tension.
