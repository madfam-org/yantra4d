# Pet Collar Hardware

Printable webbing hardware for pet collars and leashes, all sized to a standard
webbing width (**20 mm** or **25 mm**), generated with **CadQuery** (B-Rep): a
side-release buckle housing, a D-ring anchor plate for a leash or tag, and a soft
tag silencer that stops the ID tag jingling.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

> Print load-bearing parts (buckle, D-ring plate) solid in a tough material;
> print the tag silencer in a soft filament (TPU) to actually mute the tag.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Side-Release Buckle** | `side_buckle` | A female buckle housing with a receiver tube, latch windows, and a webbing bar slot. |
| **D-Ring Plate** | `d_ring` | A webbing loop plate with an integral flat D-ring for clipping a leash / tag. |
| **Tag Silencer** | `tag_silencer` | A flat pad with a tag recess and a hang slot that mutes the ID tag. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Webbing | `webbing` | 25 mm | Standard collar webbing width (20 / 25 mm). |
| Webbing | `web_th` | 2.5 mm | Webbing thickness (sets slot height). |
| Body | `wall` | 3.0 mm | Housing / plate wall. |
| Body | `clearance` | 0.4 mm | Per-side slot / latch gap. |
| Ring / Tag | `ring_dia` | 22.0 mm | D-ring inner size, or tag diameter. |

## Presets

- **25 mm Side Buckle**.
- **Leash D-Ring (25 mm)**.
- **Quiet Tag Cover**.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Collar Webbing** (`snap`, `20/25mm webbing`) — the webbing-threading and
    latch geometry, defined by `webbing`, `web_th`, `wall`, `clearance`. All
    three parts thread the same 20/25 mm webbing standard.
- **Material awareness:** `tolerance_by_material` is declared — the latch/slot
  clearance tunes to a rigid or springy material.
- **Societal benefit:** replacement hardware sized to the universal webbing
  standard extends a collar's life instead of discarding it over one broken
  buckle.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via `PARAM(lambda: name, default)`;
  final solid assigned to `result`.
- All shipped presets and defaults render **watertight**.
