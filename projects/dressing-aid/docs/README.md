# Reacher / Button-Hook Dressing Aid

Dressing aids that let a user **fasten and reach clothing** with limited hand
function. Generated with **CadQuery** (B-Rep). A button hook catches a button
through its buttonhole and pulls it through; a zipper-pull hook snags a zipper
tab so a jacket can be closed one-handed; a reacher hook grabs a waistband, sock,
or dropped item. Each is a printed hook on an enlarged, easy-to-grip handle — the
classic occupational-therapy dressing aids.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

> **Fit is user-specific.** Hook size, handle diameter, and reach depend on the
> user's hand, grip, and the garments they wear — a button hook for shirt buttons
> is not the one for a coat toggle. An occupational therapist (OT) can size these
> to the person and coach the technique. These are printed in rigid plastic
> rather than the traditional bent wire, so the hook is a solid tongue: check that
> its thickness clears the buttonhole and print a test hook before committing.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Button Hook** | `button_hook` | A slim hook on a fat handle. The hook passes through a buttonhole, catches the button, and pulls it back through — the standard one-handed buttoning aid. |
| **Zipper Hook** | `zipper_hook` | A small tight J-hook that slips into a zipper pull's hole and tugs it, so a jacket or fly closes one-handed. |
| **Reacher Hook** | `reacher_hook` | A longer neck ending in a wide open C-hook to snag a waistband, sock, or dropped item and draw it in. |

Each mode dispatches on `target_part`; the manifest `parts[]` ids (`button_hook`
/ `zipper_hook` / `reacher_hook`) match the dispatched values, so every mode
renders its own geometry.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Handle | `handle_len` | 100 mm | Length of the grip handle. |
| Handle | `handle_dia` | 28 mm | Enlarged grip diameter (bigger = easier to hold). |
| Handle | `loop_dia` | 16 mm | Finger-loop opening near the handle end. |
| Hook | `thick` | 6 mm | Stock thickness of the hook and neck (strength). |
| Hook | `hook_r` | 9 mm | Inner radius of the hook curl (`button_hook`, `reacher_hook`). |
| Hook | `hook_open` | 7 mm | Opening the hook slips over (button / tab / cloth). |
| Hook | `reach` | 45 mm | Distance from handle to the hook. |

## Presets

- **Standard Button Hook** — a slim hook on a 28 mm handle for shirt buttons.
- **Jacket Zipper Hook** — a tight J-hook for a jacket or fly zip.
- **Sock / Waistband Reacher** — a longer neck with a wide C-hook for dressing.

## Hyperobject Profile

- **Domain:** medical
- **CDG interface:**
  - **Hook + Handle Profile** (`profile`, internal) — the hook geometry and its
    handle, defined by `hook_r`, `hook_open`, `thick`, and `reach`. The mouth
    (`hook_open`) sizes what the hook engages — a button, a zipper tab, or cloth.
- **Material awareness:** `thick` and `hook_open` are exposed so the hook can be
  made stiffer or thinner and the mouth tuned per print material;
  `tolerance_by_material` is declared.
- **Societal benefit:** buttoning a shirt, closing a jacket, and pulling on socks
  are private, daily acts of independence that stroke, arthritis, a single working
  hand, or limited reach can quietly end. Printed aids sized to the user's hand
  and clothing restore self-dressing at near-zero cost, reprintable as ability
  changes — keeping a basic dignity in the user's own hands.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters are read via a `PARAM(lambda: name,
  default)` guard; `target_part` dispatches the part; the final solid is `result`.
- Each aid is one manifold solid. The handle is a plain cylinder with a filleted
  rim (no on-axis revolve singularity, no tangent sphere-union seam) and a finger
  loop cut as a through-hole; the neck is a solid bar sharing the handle mid-plane
  and overlapping into the handle so it welds solid (no thin raked plate floating
  off the grip); the hook is a single extruded open-C annular-sector profile. All
  shipped modes and both parameter extremes render **watertight**, `body_count == 1`.
