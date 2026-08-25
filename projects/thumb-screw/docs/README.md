# Knurled Thumb Screw

Printable **hand-turned fasteners** on real ISO metric threads (M5 or M6),
generated with **CadQuery** (B-Rep).

The thread is a genuine single-start helix built from **volumetric fused ribs** —
a trapezoidal profile swept along a true `makeHelix` path and unioned into the
shaft/bore — **not** a cosmetic boolean groove. So a printed thumb screw threads
into the same tapped hole or heat-set insert as a bought M5/M6 screw, and the
thumb nut runs on the same shaft.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## The half-integer thread rule

The swept thread turn count is snapped to a **half-integer** (`floor(n) + 0.5`).
An *integer* turn count degenerates the OCCT helical sweep — the profile closes
back on itself, the orientation flips, and the boolean yields a
negative-volume / null body. A half-integer is well-conditioned and much faster.
Real hand-fasteners engage only a few turns, so the engagement slider is capped at
a validated half-integer ceiling and costs nothing physical.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Thumb Screw** | `thumb_screw` | A knurled disc head on a male-threaded shaft. |
| **Thumb Nut** | `thumb_nut` | A knurled female-threaded knob (a hand-turned nut) that runs on an M5/M6 shaft — the mate for the thumb screw. |
| **Wing Screw** | `wing_screw` | A two-wing head on the same male-threaded shaft, for higher hand-torque than a knurled disc. |

All three modes render a single watertight body (`body_count == 1`).

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Thread | `thread_size` | M6 | M5 (5.0 × 0.8) or M6 (6.0 × 1.0). |
| Thread | `clearance` | 0.35 mm | Per-side fit slop (male cut thinner, female cut wider). |
| Thread | `engage_turns` | 3.5 | Thread turns, snapped to a half-integer. |
| Head | `head_dia` | 20.0 mm | Knurled head / knob diameter (wing span for the wing screw). |
| Head | `head_h` | 6.0 mm | Head thickness. |
| Head | `knurl_teeth` | 24 | Grip flutes (thumb screw / nut). |
| Shaft | `shaft_len` | 16.0 mm | Threaded shaft length (thumb / wing screw). |

### Thread stock (nominal major diameter × pitch, mm)

| Size | Major Ø | Pitch |
| :--- | :--- | :--- |
| M5 | 5.0 | 0.8 |
| M6 | 6.0 | 1.0 |

ISO 261 / ISO 965 coarse-pitch nominal values.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interface:** `iso_metric_thread` — a `thread`, standard **M5/M6**.
- **Compatible with:** `sentinel-gripper-hyperobject`. The M6 male thread mates the
  **iso-m6** family — the M6 bolt circle of the sentinel-gripper flange
  (ISO 9409-1-50-4-M6) — so a printed M6 thumb screw fastens that flange.
- **License:** CERN-OHL-W-2.0.

## Printing notes

- Print **vertically** (shaft up) for the roundest thread; a 0.2 mm layer height
  and 4 perimeters give a serviceable printed thread.
- Start at `clearance = 0.35` mm/side. If the screw is too tight in a nominal hole,
  raise it; if it is sloppy, lower it.
- Printed plastic threads are for hand-torque, not structural preload — for a
  load-bearing joint, pair a printed thumb screw with a metal nut or a heat-set
  insert.
