# Hook & Eye

The oldest garment fastener, made printable — a sprung hook that catches an eye
(loop or bar) — generated with **CadQuery** (B-Rep). Parametric across the two
places it lives: a single tailoring hook-and-bar, and the multi-column bra-back
tape (the **N×M** closure — N columns of size adjustment × M rows of hooks).
This is the solid the Fashion Cabinet `bra-wireless` and other hook-closed
garment notions bridge to.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Parts | Description |
| :--- | :--- | :--- |
| **Hook** | `hook_plate` | A sewing plate with two eyelets and a column of curled hook noses. |
| **Eye (bar)** | `eye_plate` | The mate: a plate with two eyelets and a column of raised bars the hook catches. |
| **Bra-back tape (N×M)** | `hook_plate`, `eye_plate` | A 1-column hook plate and an N-column eye plate — the standard bra-back closure with `columns` steps of band adjustment. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Closure Grid | `columns` | 3 | Eye columns on the band side — each is one band-size step (bras use 2–3). |
| Closure Grid | `rows` | 2 | Hook rows up the band height (a 2-row bra band uses 2). |
| Size | `size_mm` | 7.0 mm | Nominal hook width / bar length; drives grid pitch. |
| Size | `plate_t` | 1.6 mm | Sewing plate thickness. |
| Size | `wire_d` | 1.6 mm | Diameter of the hook curl and eye bar. |
| Print Fit | `gap` | 0.35 mm | Hook-to-bar clearance; tune so it clips but holds. |

## Presets

- **Bra Back 3×2** — the everyday bra-back closure (3 adjustment columns, 2 rows).
- **Wide Band 2×3** — a taller band with 3 hook rows.
- **Trouser Waistband Hook** — a single heavy tailoring hook (1 row, 12 mm).

## Hyperobject Profile

- **Domain:** wearable
- **CDG interfaces:**
  - **Sewing Plate** (`flange`, internal) — the plate edge the band sews to,
    defined by `size_mm`, `plate_t`.
  - **Hook / Bar Catch** (`snap`, internal) — the sprung catch itself, defined by
    `wire_d`, `gap`.
- **Fashion Cabinet bridge:** the `bra-wireless` notion references the `bra_3x2`
  configuration (`columns=3`, `rows=2`).

## Fabrication notes

Every part exports as a watertight solid. The hook curl is a **half-torus**
(revolve/`makeTorus` primitives, not a fragile swept arc) opening toward the
front so a bar drops in; the eye bar is a wire staple bridged on two posts. Print
the plates flat, hooks up, and tune `gap` (start 0.35 mm) so the closure clips but
holds. `columns` is the wearer's band adjustment — print exactly as many steps as
the band needs.
