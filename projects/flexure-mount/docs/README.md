# Compliant Flexure Mount

A **monolithic flexure stage**, generated with **CadQuery** (B-Rep). A flexure
moves precisely by **elastic bending of thin blades** instead of sliding joints —
so it has **no play, no lubrication, and no wear**, and returns to the same place
every time. Flexures are the basis of optical mounts, force probes, and precision
micro-positioners. It **mates the ISO M3 fastener family**: every mounting hole
is M3 clearance (3.4 mm), so the stage bolts to any M3 pattern.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

> **Compliant-mechanism note.** A flexure is inherently **one monolithic solid** —
> the thin blade sections are the moving elements. Every mode here is a single
> watertight body; the blades are sized (default 1.2 mm) so they print and flex
> without severing the part. Print in PLA/PETG for stiff stages or in nylon/PP
> for higher fatigue life.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Linear Flexure** | `flexure_stage` | A parallelogram (four-bar) linear flexure: a moving platform on two thin blades over a fixed frame — translates along one axis. M3 holes on frame and platform. |
| **Notch Flexure** | `notch_flexure` | A notch-hinge angular flexure: two arms joined by a thin circular-notch living hinge, with a travel-stop relief and M3 mounts at both ends. |
| **XY Flexure** | `xy_flexure` | A serial XY stage: two nested slot-rings give the central platform decoupled X and Y compliance from one monolithic part. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Body | `body_w` / `body_d` | 60 / 50 mm | Overall footprint. |
| Body | `thickness` | 10 mm | Part thickness (taller resists out-of-plane motion). |
| Flexure | `blade_t` | 1.2 mm | Blade / neck thickness — thinner is more compliant. |
| Flexure | `frame_w` | 8 mm | Rigid frame and arm width. |
| Flexure | `travel` | 6 mm | Motion gap that sets the travel range. |
| Mount | `m3_d` | 3.4 mm | M3 clearance hole. |

## How it flexes (and why it's one solid)

Each stage is cut from a **solid blank**. The **linear** flexure removes pockets
that leave two vertical blades between a fixed bar and a moving bar. The **notch**
flexure cuts two facing circular notches that leave a thin neck — the neck bends
like a hinge. The **XY** flexure cuts two nested rectangular **slot-rings**, each
as a single even-odd sketch (outer rect minus inner rect) with two blade bridges
re-added — so no two cuts share a coincident face and the body stays **manifold
and watertight** (`body_count == 1`). Because the whole mechanism is one printed
part, there is nothing to assemble and no joint to wear.

## Presets

- **Optics Linear Stage** — a general single-axis positioner.
- **Notch Hinge** — a compact angular pivot.
- **XY Positioner** — a decoupled two-axis stage.

## Hyperobject Profile

- **Domain:** hybrid
- **CDG interfaces:**
  - **Flexure Blades** (`profile`, *internal*) — the compliant blade/neck
    sections, defined by `blade_t`, `travel`, `frame_w`.
  - **M3 Mounting Pattern** (`bolt_pattern`, *ISO 261 M3*) — the M3 clearance
    holes, defined by `m3_d`. **Compatible with** the M3 family — `din-rail-clip`
    (M3/M4/M5) and `enclosure-vent` (M3).
- **Material awareness:** `tolerance_by_material` is declared — blade thickness is
  exposed so stiffness and fatigue life tune per material (stiff PLA vs tougher
  nylon/PP).
- **Societal benefit:** flexures replace bearings with elastic bending for
  play-free, wear-free precision motion; an open, parametric flexure on the
  standard M3 grid lets a lab print a precision stage tuned to its load and travel.
- **License:** CERN-OHL-W-2.0
- **Family:** mates the **ISO M3** family (`din-rail-clip`, `enclosure-vent`).

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters read via `PARAM(lambda: name,
  default)`; `target_part` dispatches which part to build; the final solid is
  assigned to `result`. Each stage is one monolithic watertight body; slot-rings
  are single even-odd booleans to stay manifold.
