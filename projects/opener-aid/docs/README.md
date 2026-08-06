# Opener Aid

Grip aids that give leverage and a non-slip hold to hands with limited strength
(arthritis, weak grip), generated with **CadQuery** (B-Rep). A stepped cone
drops over round jar and bottle lids across a range of diameters; a lever pries
crown caps; a small hook lifts stubborn can tabs.

> **These are printable everyday-living _aids_, not certified medical devices.**
> Print in a grippy material (TPU sleeves or textured PLA/PETG) for the best
> hold.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Jar Opener** | `jar_opener` | An inverted stepped cone: internal steps grip several lid diameters; the fluted outer wall is the handhold. |
| **Bottle Opener** | `bottle_opener` | A flat comfort lever with a large finger hole and a crown-cap catch. |
| **Can-Tab Opener** | `tab_opener` | A hooked lever that slips under a ring-pull can tab. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Lid Range | `lid_min` / `lid_max` | 40 / 85 mm | Smallest / largest lid diameter gripped. |
| Lid Range | `steps` | 4 | Number of internal lid-diameter steps. |
| Body & Grip | `wall` | 4.0 mm | Cone wall / lever thickness. |
| Body & Grip | `grip_h` | 16.0 mm | Height of each grip step. |
| Body & Grip | `flutes` | 12 | Vertical hand-grip flutes (0 = smooth). |
| Lever | `lever_len` | 95.0 mm | Bottle / tab lever length. |

## Presets

- **Wide-Range Jar Opener** — 40–90 mm, five steps.
- **Large Lids (mason/pickle)** — 60–120 mm.
- **Crown-Cap Lever** — a sturdy bottle lever.

## Hyperobject Profile

- **Domain:** medical
- **CDG interfaces:**
  - **Lid Grip** (`socket`, internal) — the internal stepped grip envelope,
    defined by `lid_min`, `lid_max`, `steps`, `wall`. Any lid in the range seats
    on the matching step.
- **Material awareness:** `tolerance_by_material` is declared — a soft/grippy
  material grips a lid with less clearance than rigid PLA.
- **Societal benefit:** preserves kitchen independence for people with reduced
  grip strength using one multi-size tool instead of many single-size gadgets.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via `PARAM(lambda: name, default)`;
  final solid assigned to `result`.
- All shipped presets and defaults render **watertight**.
