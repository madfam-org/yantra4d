# Endstop Mount

A **limit-switch / endstop mount**, generated with **CadQuery** (B-Rep). It holds
a switch at a repeatable position on a motion axis. The switch face carries the
**Omron-style microswitch footprint** — two M2 holes on ~9.5 mm centres for a
~20 x 6 mm subminiature switch (SS / D2F family) — and adjustment slots dial in
the trigger point.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Switch Bracket** | `switch_bracket` | A flat plate with the two microswitch holes plus two lengthwise **adjustment slots** so the bracket slides to set the trigger point. |
| **Optical Endstop** | `optical_endstop` | A plate sized for a small optical-endstop PCB — board bolt holes at the board length plus a clearance **window** for the fork/flag. |
| **2020 Extrusion Endstop** | `extrusion_endstop` | An L-foot for a 2020 T-slot extrusion: the switch bolts to the upstand, the foot drops M5 T-nuts into the slot on 20 mm centres. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Switch | `hole_span` | 9.5 mm | Microswitch bolt centres (Omron SS/D2F). |
| Switch | `switch_hole` | 2.2 mm | Switch bolt clearance (M2). |
| Plate | `plate_t` | 3.0 mm | Bracket thickness. |
| Plate | `plate_w` | 14 mm | Plate width across the switch. |
| Mount | `slot_len` | 12 mm | Adjustment slot travel (switch bracket). |
| Mount | `mount_d` | 5.2 mm | Frame / extrusion bolt (M5 T-nut). |
| Plate | `board_len` | 33 mm | Optical PCB length / hole spacing. |
| Plate | `board_hole` | 3.2 mm | Optical PCB bolt (M3). |
| Mount | `foot_len` | 28 mm | Extrusion foot length. |

## The switch footprint (why it fits)

A subminiature microswitch (Omron SS, D2F and clones) mounts through **two M2
holes on ~9.5 mm centres**. The bracket cuts exactly that pattern so any of these
interchangeable switches bolts on. The adjustment slots then let the whole bracket
slide along the frame bolt, so the trigger point is set mechanically instead of in
firmware. Plates are filleted **as clean blanks before** holes and slots are cut,
keeping every mode watertight.

## Presets

- **Omron Microswitch** — the standard slotted switch bracket.
- **Optical PCB** — mount for a fork optical endstop board.
- **2020 Endstop Foot** — extrusion-frame foot with a switch upstand.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **Microswitch Mount** (`bolt_pattern`, *Omron SS/D2F*) — the two-hole switch
    pattern, defined by `hole_span`, `switch_hole`. Fits the standard subminiature
    switch footprint.
  - **Frame Mount** (`bolt_pattern`, *internal*) — the slot / foot mounting holes,
    defined by `mount_d`, `slot_len`, `foot_len`.
- **Material awareness:** `tolerance_by_material` is declared — bolt clearances can
  be tuned per material.
- **Societal benefit:** a printed mount cut to the standard Omron microswitch
  footprint, with adjustment slots, lets any salvaged limit switch home a machine
  precisely, even on a modified frame.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters read via `PARAM(lambda: name,
  default)`; `target_part` dispatches which part to build; the final solid is
  assigned to `result`. All modes render **watertight**.
