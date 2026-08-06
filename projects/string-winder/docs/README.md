# String Winder / Peg Aid

The **peg winder** every guitarist keeps in the case, generated with **CadQuery**
(B-Rep): a crank whose **socket fits over the tuning-machine button** so strings
wind up fast, plus a notch that pops acoustic bridge pins.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Peg Winder** | `peg_winder` | A crank handle ending in a cupped button socket, with a bridge-pin puller notch in the rim — the classic tool. |
| **Bridge-Pin Puller** | `pin_puller` | A standalone fork lever that hooks under an acoustic bridge-pin head and levers it out. |
| **Multi-Socket Knob** | `multi_socket` | A fluted knob carrying three button sockets of different widths so one tool fits open-gear, sealed and classical tuners. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Button Socket | `button_w` | 16.0 mm | Tuner-button width across the flats (~14-19 mm typical). |
| Button Socket | `socket_dep` | 10.0 mm | How deep the button seats. |
| Button Socket | `fit_clear` | 0.4 mm | Per-side gap so the socket slips over the button. |
| Handle | `handle_len` | 70.0 mm | Crank / lever handle length. |
| Bridge Pin | `pin_slot` | 5.5 mm | Slot that hooks the acoustic bridge-pin head. |
| Handle | `wall` | 4.0 mm | Socket wall / body thickness. |

## The tuner-button interface

Guitar, bass and ukulele machine heads share a **near-standard button** — an
oval/slabbed knob roughly 14-19 mm across the flats on a ~6 mm post. The winder
socket is an **obround cup** that grips both round and slabbed buttons; `fit_clear`
tunes the slip fit per printer. The rim carries a `pin_slot` notch that hooks
under an acoustic **bridge-pin** head (~5-6 mm) to pop it, so one tool both winds
and unpins.

## Presets

- **Acoustic Peg Winder** — the standard crank + pin notch.
- **Bridge-Pin Puller** — a dedicated fork lever.
- **Three-Size Socket Knob** — one knob, three button widths.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interface:** **Tuner Button Socket** (`socket`, *standard tuner button
  ~14-19 mm, 6 mm post*) — the cupped socket, defined by `button_w`, `socket_dep`,
  `fit_clear`.
- **Material awareness:** `tolerance_by_material` is declared — `fit_clear` is
  exposed so the socket grip tunes per material/printer.
- **Societal benefit:** hand-winding strings is slow and a lost winder means a
  gig-day scramble; the button is a near-standard shape, so a printed winder fits
  almost any instrument and pops bridge pins too.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via a `PARAM(lambda: name, default)`
  guard; `target_part` dispatches the part; the final solid is `result`.
- The button socket is a **blind cup** bored from the open end (vented); the
  bridge-pin slot and fork are **obround** cuts open to a face (no trapped void);
  the handle is a solid **obround capsule** unioned into the boss (mesh-robust vs
  a two-wire loft). All modes render **watertight**, single-body.
