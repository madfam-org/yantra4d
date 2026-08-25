# Soft Pneumatic Finger

A **single-body pneumatic bending finger** for soft robotics, generated with
**CadQuery** (B-Rep). The finger is a solid ribbed beam: an **accordion of
bellows ribs** on the extension (top) side and a **flat strain-limiting base** on
the bottom, so pressurising the internal chamber makes the top stretch while the
base stays put — the finger curls. A single **internal air chamber** runs the
length of the finger and **opens to the proximal face** at a **barbed air port**
sized for **4 mm ID / 6 mm OD** pneumatic tubing.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

> **Compliant-mechanism note.** This is modelled as a **printable single-body
> solid** with **no trapped sealed void** — the air chamber vents to the
> proximal face, so the whole mesh is watertight. Printed rigid (PLA/PETG) it is
> a **geometry master / casting pattern**: cast it in silicone, or print the
> walls in **TPU**, to get a part that actually inflates. A fully rigid print
> will not bend.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Bellows Finger** | `bellows_finger` | The full ribbed bending finger with the internal air chamber and a barbed 4/6 mm air port on the base face. |
| **Grip Tip** | `finger_tip` | A rounded, friction-ribbed grip cap with a socket that press-fits the finger's distal end — a reprintable fingertip / wear pad. |
| **Base Air Port** | `base_port` | Just the proximal mounting flange: a block with the barbed 4/6 mm port and two M3 screw ears, for a modular hand where fingers bond onto shared bases. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Finger Body | `finger_len` | 80 mm | Length along the bend axis. |
| Finger Body | `finger_w` | 20 mm | Finger width. |
| Finger Body | `body_h` | 14 mm | Body height including bellows ribs. |
| Bellows | `n_ribs` | 8 | Accordion ribs — more ribs bend tighter. |
| Bellows | `wall` | 2.0 mm | Chamber wall thickness (thinner → more inflation in TPU). |
| Bellows | `chamber_w` | 12 mm | Internal air-chamber width. |
| Air Port | `barb_od` / `barb_id` | 6 / 4 mm | Barbed port for 6 mm OD / 4 mm ID tube. |

## Why it bends (and why it's watertight)

The chamber is a **blind pocket** cut inward **from the proximal face**, stopping
short of the distal cap. Because its mouth lies on an exterior face, there is **no
enclosed cavity** — `is_watertight == True` and `body_count == 1` for every mode.
The barbed port is a stepped cylinder on that same face with a through bore into
the chamber; a retention ridge near the tip holds 6 mm OD tubing. The bellows
ribs are full-height blocks over a thin continuous spine, so the top surface is
an accordion while the base is a flat plate — the standard soft-actuator
"PneuNet" strategy, expressed as a printable master.

## Presets

- **Standard 80 mm Finger** — a general-purpose curling finger.
- **Short Stiff Finger** — shorter, wider, fewer ribs for a firmer grip.
- **Modular Base Port** — the shared base flange for a multi-finger hand.

## Hyperobject Profile

- **Domain:** hybrid
- **CDG interfaces:**
  - **Pneumatic Air Port** (`socket`, *4/6mm pneumatic tube*) — the barbed port,
    defined by `barb_od`, `barb_id`. Accepts standard 4 mm ID / 6 mm OD soft
    tubing shared across the pneumatics ecosystem.
  - **Bellows Chamber** (`profile`, *internal*) — the accordion rib profile and
    internal chamber, defined by `n_ribs`, `chamber_w`, `wall`.
- **Material awareness:** `tolerance_by_material` is declared — wall thickness is
  exposed so the same finger can be printed as a rigid master or as a thin-wall
  TPU actuator.
- **Societal benefit:** soft grippers handle fragile, irregular objects that
  rigid jaws crush; an open parametric finger with a standard air port lowers the
  cost barrier for soft-robotics research and assistive devices.
- **License:** CERN-OHL-W-2.0
- **Family:** new soft-robotics cluster (no existing mate).

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters read via `PARAM(lambda: name,
  default)`; `target_part` dispatches which part to build; the final solid is
  assigned to `result`. Every mode is a single watertight body with the air
  chamber vented to a face (no trapped void).
