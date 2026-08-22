# Bra Underwire + Tip Cap

The printable underwire arc and its protective tip caps — generated with
**CadQuery** (B-Rep). Fashion Cabinet's [`bra-underwire`](https://fc.madfam.io)
notion owns the fashion semantics (cup geometry, cradle seam placement, channel
construction) and bridges to **this** solid for the hardware.

Feeds the `underwear_lounge` family alongside
[`hook-and-eye`](../../hook-and-eye) (the back closure) and
[`bra-ring-slider`](../../bra-ring-slider) (the strap adjusters).

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Wire + Two Tip Caps** | `set` | One arc laid flat with both tip caps beside it — the printable set for one cup. |
| **Underwire Arc** | `wire` | Just the arc: a trimmed round-section torus with rounded ends. |
| **Tip Cap** | `tip_cap` | Just one cap: a short closed tube that slips over a wire end. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Wire | `cup_width` | 120 mm | Straight-line span between the wire ends = arc diameter. Driven by the finished cup width. |
| Wire | `wire_d` | 2.5 mm | Wire section diameter. Also sets the cap bore (`wire_d + 0.3` clearance), keeping the pair matched. |
| Wire | `sweep_deg` | 180° | Arc angular span, 150–210°. Under 180° is a shallow open wire; over 180° wraps further under the cup. |
| Cap | `cap_len` | 8 mm | Overall cap length; longer caps spread the end load over more channel. |
| Cap | `cap_wall` | 1.2 mm | Cap wall thickness, including the rounded closed end. |

Safety limits live in `main.py` clamps, not manifest constraints: `cap_wall` is
capped at `cap_len / 3` and `wire_d` at `cup_width / 8`, so no slider combination
can produce a capless tube or a self-intersecting arc.

## Print notes

Print the wire **flat in the XY plane**, arc lying down — that keeps the whole
length on the bed with no supports and puts the layer lines across the section
rather than along it. Use a springy filament (**nylon** or **PETG**) if the wire
is to actually work in a garment; rigid PLA prints a good fitting/sizing gauge but
will snap in wear. Tip caps print standing on their open end, closed dome up. A
0.4 mm nozzle at 0.15 mm layers holds the `wire_d + 0.3` bore clearance; the caps
should push on with a firm friction fit and can be secured with a drop of fabric
glue. Both parts print well in recycled and offcut material
(`recycled_material_toggle` in the profile).

## Hyperobject Profile

- **Domain:** wearable
- **CDG interfaces:**
  - **Channel Fit** (`socket`, internal) — the sewn wire casing the arc rides in,
    defined by `wire_d`, `cup_width`.
  - **Tip Bore** (`socket`, internal) — the cap's blind bore over the wire end,
    defined by `wire_d`, `cap_len`.
  - **Cradle Seam Flange** (`flange`, internal) — **the sewn/set edge for the
    dimensional handshake**: the cradle seam line the arc is set against, defined
    by `cup_width`, `sweep_deg`, `wire_d`. FC matches its finished cradle seam
    length to this interface.

## Fashion Cabinet bridge

FC-side `hardware_ref` block for the `bra-underwire` notion:

```json
{
  "notion": {
    "hardware_ref": {
      "platform": "yantra4d",
      "project_slug": "bra-underwire",
      "linked": true,
      "params_map": {
        "cup_width": "cup_width_mm",
        "wire_d": "underwire_gauge_mm",
        "sweep_deg": "cradle_sweep_deg",
        "cap_len": "wire_channel_end_mm",
        "cap_wall": "wire_channel_end_mm * 0.15"
      }
    }
  }
}
```

The dimensional handshake runs through **`cradle_seam`**: FC's finished cup width
sets `cup_width`, and FC's cradle sweep sets `sweep_deg`, so the printed arc lands
on the garment's own seam line rather than on a retail wire size.

## License

**CERN-OHL-W-2.0** — open hardware, share-alike on the weak-reciprocity terms.
