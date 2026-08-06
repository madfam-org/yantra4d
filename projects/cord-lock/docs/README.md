# Cord-Lock / Toggle Stopper

A small toggle generated with **CadQuery** (B-Rep) that locks drawstrings and
cords on apparel, bags, and gear. Single-piece, print-in-place designs that stay
watertight: a spring toggle with a printed pincher, a friction bead, or a squeeze
cleat. Sized to the cord; holds 1 or 2 cords.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Spring Toggle** | `lock` | A barrel with a cord channel and a printed compliant tongue (freed by a U-slot) that pinches the cord; squeeze to release. |
| **Simple Toggle** | `lock` | A friction bead: a cord channel plus an offset locking slot that kinks the cord to hold it. |
| **Squeeze Cleat** | `lock` | A flat block with a V-throat that wedges the cord, plus a mounting hole. |

The `lock_style` selector (`spring_button` / `twist` / `clam`) picks the same
three mechanisms independently of `target_part`.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Cord | `cord_dia` | 4.0 mm | Cord / drawstring diameter. |
| Cord | `cords` | 1 | 1 or 2 cords through the lock. |
| Body | `lock_style` | spring_button | Spring / twist / clam mechanism. |
| Body | `body_size` | 14 mm | Nominal body size (barrel dia / cleat height). |
| Body | `wall` | 2.0 mm | Wall and spring-rib thickness. |

## Presets

- **Hoodie Spring Toggle (4 mm)** — a two-cord sprung toggle for a hoodie.
- **Backpack Friction Bead (5 mm)** — a single-cord friction bead.
- **Tent Guy-Line Cleat (3 mm)** — a squeeze cleat for a tent guy line.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Cord Pincher** (`snap`, internal) — the printed compliant clamp, defined
    by `cord_dia`, `cords`, `wall`. This is the flexure interface that grips the
    cord; sizing it to `cord_dia` is what makes it hold.
  - **Cord Channel** (`pocket`, internal) — `cord_dia`, `cords`, `body_size`
    define the through-channels the cord threads into.
- **Material awareness:** the pincher and channel clearances scale with
  `cord_dia` and `wall` so the grip can be tuned per material/printer;
  `tolerance_by_material` is declared (TPU grips a cord differently than PLA).
- **Societal benefit:** cord locks are the tiny plastic part that fails first and
  can never be found to replace — a print-in-place stopper sized to any cord
  keeps a jacket, bag, or tent in service instead of the landfill.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard; the final solid is assigned to `result`.
- Every mode is a **single continuous watertight solid** — the spring toggle's
  tongue is freed by cut slots but stays attached at its root (one connected
  component), so it prints in place with no assembly.
