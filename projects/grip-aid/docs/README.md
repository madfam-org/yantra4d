# Key / Zipper Grip Aid

Grip enlargers for the small, hard-to-turn objects of daily life — **keys,
zipper pulls, and small tabs**. Generated with **CadQuery** (B-Rep). Each part
captures a thin flat tab in a pocket and gives it a large, easy-to-hold body so a
user with limited pinch strength, arthritis, tremor, or one-handed use can turn,
pull, or grasp it.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

> **Fit is user-specific.** Measure the actual tab you are enlarging — the width
> and thickness of the key bow, zipper slider, or toggle — and check the hold
> against the user's hand. What counts as "easy to grip" depends on the person;
> an occupational therapist (OT) can advise on body size, shape, and the pinch
> vs. whole-hand trade-off. Print one, try it, and adjust the slot gap.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Key Turner** | `key_turner` | A broad rounded wing. The key's bow slides into a slot at one end; a cross-hole takes the split ring or a retaining pin. The wide body multiplies torque so a stiff lock turns with the whole hand. |
| **Zipper Pull** | `zip_pull` | A teardrop pull with a finger-loop through-hole and a small bar-slot at the tip that threads onto a zipper slider's pull-hole. |
| **Tab Grip** | `tab_grip` | A rounded knob whose slot grips a small flat tab or cord toggle for an easy push/pull; a cross pin locks the tab in. |

Each mode dispatches on `target_part`; the manifest `parts[]` ids (`key_turner` /
`zip_pull` / `tab_grip`) match the dispatched values, so every mode renders its
own geometry.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Grip Body | `grip_len` | 55 mm | Overall length of the body. |
| Grip Body | `grip_w` | 24 mm | Width across the hold. |
| Grip Body | `thick` | 12 mm | Body thickness (grip depth in the hand). |
| Tab Capture | `tab_w` | 9 mm | Width of the captured tab (key bow / pull / toggle). |
| Tab Capture | `tab_t` | 2.4 mm | Slot gap that grips the tab (a key blade is ~2.4 mm at the bow). |
| Tab Capture | `tab_depth` | 12 mm | Insertion depth (`key_turner`, `tab_grip`). |
| Tab Capture | `pin_dia` | 3.2 mm | Cross-hole for a split ring or retaining pin. |
| Tab Capture | `loop_dia` | 14 mm | Finger-loop opening (`zip_pull`). |

## Presets

- **House-Key Turner** — a 55 mm wing sized to a typical key bow.
- **Coat Zipper Pull** — a thin teardrop with a finger loop for a jacket zip.
- **Cord-Toggle Grip** — a knob for a drawstring or pull-cord toggle.

## Hyperobject Profile

- **Domain:** medical
- **CDG interface:**
  - **Flat-Tab Capture Pocket** (`pocket`, internal) — the slot that captures the
    flat tab, defined by `tab_w`, `tab_t`, and `tab_depth`. Any key bow, zip
    slider, or toggle within those dimensions seats in the grip.
- **Material awareness:** `tab_t` (the slot gap) is exposed so the friction grip
  on the tab can be tuned for rigid (PLA/PETG) or soft (TPU) filament;
  `tolerance_by_material` is declared.
- **Societal benefit:** turning a key, closing a zipper, and pinching a toggle are
  everyday tasks that quietly fail with arthritis, reduced grip, tremor, or a
  single usable hand. A grip enlarger sized to the exact tab restores those tasks
  with the whole hand for the cost of a few grams of filament.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters are read via a `PARAM(lambda: name,
  default)` guard; `target_part` dispatches the part; the final solid is `result`.
- Each body is one manifold solid. Capture slots are kept narrower than the body
  so a wall always remains on both sides (they never split the end into prongs)
  and open to an outer face (vented); the finger loop and pin holes are
  through-holes; the teardrop is built from overlapping lobes joined by a bar (no
  tangent seam); the knob is a single loft to a flat top disc (never a singular
  apex). All shipped modes and both parameter extremes render **watertight**,
  `body_count == 1`.
