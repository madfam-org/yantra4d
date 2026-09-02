# DIN Rail End Stop

The parts that terminate a rail, rather than ride on it.

A **CadQuery** B-Rep hyperobject — every mode renders watertight and exports STEP. Un hiperobjeto **CadQuery** B-Rep: cada modo es hermético y exporta STEP. Un hyperobjet **CadQuery** B-Rep : chaque mode est étanche et exporte en STEP. Um hiperobjeto **CadQuery** B-Rep: cada modo é estanque e exporta STEP.

Part of the **Yantra4D Hyperobjects Commons** · Official visualizer: [Yantra4D](https://app.yantra4d.com)

## Why this exists

The commons has **seven** cartridges that clip *to* DIN EN 60715 TS35 rail — `din-module`, `din-relay`, `din-rail-clip`, `din-terminal-comb`, `terminal-cover`, `busbar-support`, `devboard-tray`.

Not one of them addresses **the rail**. Nothing stops a row of modules sliding along it, nothing spaces two groups apart, and nothing fills an empty way so fingers and dust stay out.

A rail with no end stop is a rail whose contents migrate every time the cabinet is transported. That is not a cosmetic problem: it loads the terminals sideways, opens gaps at the busbar, and eventually leaves a live way exposed.

**Seven existing members mate a single rail interface, at the lowest build effort in the tranche** — the largest genuine-standard edge yield per unit of work in the whole wave.

## Modes

| Mode | Label | What it is |
| :--- | :--- | :--- |
| `end_stop` | End Stop | The terminating bracket: clip back, a tall stop face, and a marker-card recess |
| `rail_spacer` | Rail Spacer | A low spacer filling a gap between two groups of modules, with a comb of cable slots across its top |
| `blank_module` | Blanking Module | A blank on the modular device pitch, filling an empty way so the busbar behind it is not open to a finger |

## What is asserted, and what is a slider

Rail geometry is **not invented here**: `RAIL_SPAN` (35.0), `LIP_GRIP` (5.0), `CLEAR` (0.35) and the hook profile mirror `din-module`'s published geometry exactly, so an end stop and a module grip the same rail identically.

For the blanking module, exactly one figure is asserted as law: **the 17.5 mm modular device pitch of DIN 43880.** That is the defining number of the format. The module's front height (45 mm) and its depth (45 mm) are the common values and are exposed as **sliders, not assertions** — depth classes vary, and the honest instruction is to measure the breaker beside the gap you are filling so the blank finishes flush rather than proud or sunk.

The far jaw of every mode is a **compliant mechanism**: a folded cantilever whose bend energy lives in the beam geometry, so the wall is never held in permanent strain. That is what keeps a printed stop from creeping off the rail over years in a warm cabinet.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **DIN TS35 Rail** (`rail`, `DIN EN 60715 TS35`)
  - **Modular Device Pitch** (`profile`, DIN 43880, 17.5 mm per unit)
  - **Compliant Spring Hook** (`snap`, internal — stiffness is a declared parameter, not a hidden constant)
- **Measured partners:** **7** — `busbar-support`, `devboard-tray`, `din-module`, `din-rail-clip`, `din-relay`, `din-terminal-comb`, `terminal-cover` — verified by running `normalize_family()` and the shipped geometry rules over the live catalog. This is exactly the count the wave plan predicted, with no taxonomy caveat.
- **Material awareness:** shrinkage compensation, tolerance-by-material. **Recycled material is deliberately disabled** — the sprung hook must keep its spring for years in a warm cabinet.
- **License:** CERN-OHL-W-2.0

## Printing and using it

Print **back-plate down**, 3–4 perimeters, 30 % infill. The hooks then form with their layer lines across the jaw rather than along the flex.

Use **PETG, ABS/ASA or nylon** in anything that gets warm. PLA loses its spring well below the temperature a loaded cabinet reaches on a summer afternoon.

### Scope — read this

**A printed blanking module is a mechanical and dust barrier. It is not an electrical safety device and it carries no rating of any kind** — no IP rating, no arc rating, no glow-wire or flammability classification, no dielectric strength. It does not make an energised board safe to work on, and it is not a substitute for a manufacturer's blank in an installation that must be certified. Mains work belongs to a competent person with the supply isolated. If your jurisdiction requires listed components in a consumer unit — and most do — this part is for a de-energised training board, a low-voltage cabinet, or a temporary cover until the real one arrives.

## Verification

Every mode was rendered through the **real** `cq_runner` sandbox at the manifest defaults, at the **min and max of every slider that applies to the mode**, at **every option of every select**, at the **all-min and all-max corners**, and at every declared preset. **49 cases, 49 pass**, each asserted `is_watertight == True`, `body_count == 1`, positive volume and a finite non-degenerate bounding box.

Bounding-box range across the whole sweep:

| Mode | min (mm) | max (mm) |
| :--- | :--- | :--- |
| `end_stop` | 44.2 × 4.0 × 22.0 | 44.2 × 40.0 × 87.5 |
| `rail_spacer` | 44.2 × 4.0 × 18.5 | 44.2 × 40.0 × 31.5 |
| `blank_module` | 44.2 × 17.5 × 30.0 | 70.0 × 140.0 × 97.5 |

**One defect was found before the sweep even started, at the defaults, and it is the sealed-void trap in its purest form.**

Both the end stop's lightening pocket and the blank module's two finger recesses were cut with a tool sized `depth + 1` but **centred on the material**, so the tool stopped about 0.25 mm short of the face it was supposed to open. The result was not a hole in the side — it was an **internal cavity**. The solid came back **watertight** (`is_watertight == True`), with **two bodies for the end stop and three for the blank**, because trimesh counts each cavity's inner shell as a body of its own. Nothing about the render, the kernel or the watertightness check objected. The fix is a named helper, `_side_pocket`, whose only job is to make the tool run **past** the face by a full millimetre; it is a helper rather than an inline expression precisely so that a later edit cannot reintroduce the arithmetic by accident.

One trap was designed out before it could bite, because the failure mode was predictable from the geometry: **the body width always contains the hooks.** `module_h` can be set as low as 25 mm, and the hooks live between 14.5 and 20.1 mm from the axis — a body derived from `module_h` alone would sit entirely inside the hook span, the hooks would touch nothing, and the render would be **three separate, individually watertight solids**. `BODY_W` is therefore `max(module_h, RAIL_SPAN + 2·HOOK_WALL + 4)`.

The rest held on the first pass because the rules were already paid for: every hook reaches *up into* the body it fuses to rather than meeting it at a face; the cable-comb slot count is derived from the space that survives the end margins rather than picked first and trimmed; the blank module is solid rather than shelled; and no fillet is taken on any edge a slot has touched.
