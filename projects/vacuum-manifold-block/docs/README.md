# Vacuum Manifold Block

The middle of the soft-pneumatic chain — **source → manifold → actuator** —
generated with **CadQuery** (B-Rep). A solid prism drilled with one plenum running
its length, an inlet at one end, and N outlet ports on a fixed pitch. Feed it
vacuum and it drives an array of `suction-cup-bellows`; feed it pressure and it
drives `bellows-actuator` or `pneu-net-finger`.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

> **LOW-PRESSURE / vacuum service only.** Print with generous perimeters — a
> printed manifold leaks at the layer seams if the walls are thin.

## Why this cartridge exists

With this cartridge the soft-pneumatic chain is **complete**: `pneumatic-barb-port`
defines the connector, the manifold distributes, and the three actuators consume.
Every port here speaks the shared barb series, so a manifold generated at one
`tube_id` mates every cartridge in the family generated at the same `tube_id`.
The port pitch is published as a **grid** interface, so a cup array can be laid out
against it without measuring anything.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Inline Manifold** | `inline_manifold` | N outlets along one face, inlet on the end — the common bar. |
| **Dual-Face Manifold** | `dual_manifold` | Outlets on both long faces (2N total), for a double row. |
| **Blanking Plug** | `blank_plug` | A plug to blank an unused outlet. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Block | `block_len` | 90.0 mm | Block length — with the pitch, this sets how many outlets fit. |
| Block | `block_w` | 18.0 mm | Block width. |
| Block | `block_h` | 16.0 mm | Block height. |
| Ports | `port_pitch` | 20.0 mm | **The published CDG grid** — outlet centre spacing. |
| Ports | `plenum_dia` | 6.0 mm | Internal gallery bore. |
| Ports | `tube_id` | 4.0 mm | Tubing inner diameter — the shared barb series. |
| Ports | `bore` | 2.6 mm | Flow diameter through each port. |
| Ports | `barb_rise` | 0.7 mm | Barb ridge height. |
| Ports | `wall` | 3.0 mm | Minimum material kept around every bore. |
| Mount | `mount_dia` | 4.3 mm | End mounting-hole clearance (4.3 = M4). |

**Port count is derived**, not entered: it follows from `block_len` and
`port_pitch`, floored at 1.

## Presets

- **4-Way Vacuum Bar** — the default cup-array driver.
- **8-Way Dual Row** — outlets on both faces.
- **Micro 3 mm Bar** — a compact bar on the 3 mm series.
- **Spare Blanking Plug** — for an unused outlet.

## Hyperobject Profile

- **Domain:** soft-robotics
- **CDG interfaces:**
  - **Pneumatic Barb Series** (`profile`, 2 / 3 / 4 mm tube ID) — `tube_id`,
    `bore`, `barb_rise`. Compatible with `pneumatic-barb-port`,
    `bellows-actuator`, `pneu-net-finger`, `suction-cup-bellows`.
  - **Outlet Pitch Grid** (`grid`, internal) — `port_pitch`, `block_len`,
    `block_w`. Compatible with `suction-cup-bellows`: lay out the cup array on
    the same pitch and the plumbing is already correct.
  - **Plenum Gallery** (`socket`, internal) — `plenum_dia`, `wall`, `block_h`.
- **Material awareness:** `wall` is exposed as the leak-critical parameter;
  `tolerance_by_material` is declared.
- **Societal benefit:** commercial vacuum manifolds are sold per-port at
  machine-shop prices, which is why teaching labs end up with a tangle of tees.
  Publishing the pitch and the barb series as interfaces lets a lab print exactly
  the outlets it needs, at the pitch its array already uses.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard; the final solid is assigned to `result`.
- **Watertight strategy:** pure boolean drilling of a prism. The plenum is one cut
  stopping short of both end walls; every port bore is a cut that intersects the
  plenum; barb stems are unioned onto the prism **before** their bores are cut, so
  no ring is ever left floating. Every bore radius is clamped against the wall so a
  bore can never break out of the block; mounting holes are **skipped entirely**
  when the block is too narrow to clear the plenum.
- All shipped presets, defaults, **and the minimum/maximum of every parameter**
  render **watertight** (single body).
