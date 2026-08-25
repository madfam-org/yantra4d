# Tendon-Driven Knuckle

A **cable-driven articulated knuckle** for soft and underactuated robotic hands,
generated with **CadQuery** (B-Rep). A tendon (fishing line, Dyneema, or steel
cable) runs through a **flexor channel** on the palm side; pulling it curls the
joint, while a **return elastic** on the back straightens it — the classic
tendon-driven finger used in low-cost prosthetics and research hands.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

> **Compliant-mechanism note.** Each part is a **printable single-body solid**;
> the tendon channels and pin bores are **through-holes that vent to faces**, so
> there is no trapped void and the whole mesh is watertight. Print rigid links in
> PLA/PETG, or compliant ones in TPU.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Knuckle Joint** | `knuckle` | An articulated joint block: a two-pronged **clevis** on the proximal end and a **tongue** on the distal end (they interlock through a pivot pin), with a flexor tendon channel and a dorsal extensor groove. |
| **Finger Segment** | `finger_segment` | A straight phalanx with two through tendon channels (flexor + return) and a **soft-hinge V-notch** — chain several with cord for an underactuated finger. |
| **Tendon Pulley** | `tendon_pulley` | A grooved winch **pulley/spool** the tendon wraps, with a drive-shaft bore, a tendon anchor hole, and a radial set-screw hole. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Segment | `seg_len` | 26 mm | Length along the finger. |
| Segment | `seg_w` | 18 mm | Segment width. |
| Segment | `seg_h` | 16 mm | Segment height. |
| Joint & Tendon | `pin_d` | 3.0 mm | Pivot-pin diameter. |
| Joint & Tendon | `tendon_d` | 2.0 mm | Tendon / cord channel diameter. |
| Joint & Tendon | `wall` | 2.4 mm | Wall around the tendon channels. |
| Pulley | `pulley_d` | 24 mm | Pulley outer diameter. |
| Pulley | `shaft_d` | 5.0 mm | Drive-shaft bore. |

## How it articulates

The **knuckle** is built by unioning overlapping boxes into one solid — a central
spine with a distal **tongue** and a proximal **clevis** (two prongs with a gap
between them). The next segment's tongue drops into this clevis and a **pivot
pin** passes across both through cut bores. A **flexor channel** runs the length
of the palm side; pull the cord through it and the chain of knuckles curls. A
**dorsal groove** carries a return elastic. The **pulley** winds the flexor cord
from a motor shaft; its groove is a narrow waist between two flanges (stacked
cylinders → one solid), and the set-screw locks it to the shaft.

## Presets

- **Index Knuckle** — a standard finger joint.
- **Phalanx Segment** — a straight link for a multi-segment finger.
- **Drive Pulley** — the motor-side spool.

## Hyperobject Profile

- **Domain:** hybrid
- **CDG interfaces:**
  - **Tendon Channel** (`custom`, *internal*) — the flexor/return cord routing,
    defined by `tendon_d`, `wall`.
  - **Pin Joint** (`socket`, *internal*) — the pivot-pin bore geometry, defined
    by `pin_d`, `seg_h`.
- **Material awareness:** `tolerance_by_material` is declared — wall and channel
  sizes are exposed so links can be rigid (PLA) or compliant (TPU) per material.
- **Societal benefit:** tendon-driven fingers are the basis of low-cost
  prosthetic and research hands; an open, parametric knuckle lets a maker or
  clinic size a hand to a wearer and reprint a broken segment.
- **License:** CERN-OHL-W-2.0
- **Family:** new soft-robotics cluster (no existing mate).

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters read via `PARAM(lambda: name,
  default)`; `target_part` dispatches which part to build; the final solid is
  assigned to `result`. Every mode is one watertight body with channels vented to
  faces (no trapped void).
