# Pi DIN Carrier

A single-board computer, clipped onto TS35 top-hat rail.

A **CadQuery** B-Rep hyperobject — every mode renders watertight and exports STEP. Un hiperobjeto **CadQuery** B-Rep: cada modo es hermético y exporta STEP. Un hyperobjet **CadQuery** B-Rep : chaque mode est étanche et exporte en STEP. Um hiperobjeto **CadQuery** B-Rep: cada modo é estanque e exporta STEP.

Part of the **Yantra4D Hyperobjects Commons** · Official visualizer: [Yantra4D](https://app.yantra4d.com)

## Why this exists

Industrial deployment is standard-shaped, not bespoke. A control cabinet is a length of **DIN EN 60715 TS35** rail and a row of things that clip to it, and the commons already had seven of those things — `din-module`, `din-relay`, `din-rail-clip`, `din-terminal-comb`, `terminal-cover`, `busbar-support`, `devboard-tray`.

It also had two cartridges built around the **Raspberry Pi hole pattern** — `pi-hat-case` and `sbc-case`.

Nothing joined the two families. So a board being deployed *industrially* had to be zip-tied to something, taped inside a box, or left on the floor of a cabinet where the next person to open it will put a screwdriver through it.

This carrier is that joint: the Pi HAT / Model B mounting pattern on one face, the TS35 rail interface on the other. **Nine live cartridges mate it, every one of them on a genuine numbered standard** — the largest measured yield in this tranche that carries no taxonomy caveat at all.

## Modes

| Mode | Label | What it is |
| :--- | :--- | :--- |
| `rail_carrier` | Rail Carrier | The carrier: a plate with a rigid reference hook and a **compliant sprung hook** on the TS35 span, and standoffs on the board pattern |
| `hat_hood` | HAT Hood | A vented hood that bolts to the **same** pattern and clears a HAT stack — finger protection and dust cover in one part |
| `riser_frame` | Riser Frame | A stacking frame that lifts a second board on the same pattern, with a cable window through the middle |

## The rail geometry is not invented here

`RAIL_SPAN` (35.0), `LIP_GRIP` (5.0), `CLEAR` (0.35) and the hook profile **mirror `din-module`'s published geometry exactly**. A carrier that grips a rail 0.2 mm differently from the module beside it is a second convention, not an interface.

The far jaw is a **compliant mechanism**: a slender folded cantilever whose bend energy lives in the beam geometry, so the wall is never held in permanent strain. That matters over years in a warm cabinet, where a part gripping by wall strain creeps off the rail. `spring_thick` sets the stiffness, and the manifest warns above 3 mm, where the cantilever stops flexing and the clip has to be forced on — which puts the load into the plate instead of the beam.

`rail_depth_class` selects between the two TS35 sections, **35 × 7.5** and **35 × 15**. Both share the same 35 mm span across the lips, so the hooks catch identically; only the jaw depth changes.

## The board pattern is a slider, and 58 × 49 is its default

58 × 49 mm with 2.75 mm holes is the published Raspberry Pi HAT / Model B mounting spec — not a measurement of one board. The sliders exist because the same carrier serves any board whose holes you can measure; the `pi_zero` preset moves Y to 23 mm on the same 58 mm X.

Standoff height defaults to 6 mm and the manifest warns below 4: leave room for the solder tails on the underside. **A board pulled down onto its own header pins cracks at the pad, not at the standoff.**

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **DIN TS35 Rail** (`rail`, `DIN EN 60715 TS35`) — mates all seven live rail cartridges.
  - **Raspberry Pi HAT Pattern** (`bolt_pattern`, 58 × 49 mm) — mates `pi-hat-case` and `sbc-case`.
  - **Compliant Spring Hook** (`snap`, internal) — the folded cantilever; stiffness is a declared parameter, not a hidden constant.
- **Measured partners:** **9**, verified by running `normalize_family()` and the shipped geometry rules over the live catalog rather than by reading them: `busbar-support`, `devboard-tray`, `din-module`, `din-rail-clip`, `din-relay`, `din-terminal-comb`, `terminal-cover`, `pi-hat-case`, `sbc-case`.
- **Material awareness:** shrinkage compensation, tolerance-by-material. **Recycled material is deliberately disabled** — the sprung hook relies on layer adhesion holding its spring over years in a warm cabinet, and reground feedstock has unpredictable interlayer strength.
- **License:** CERN-OHL-W-2.0

## Printing and using it

Print **plate-down**, 4 perimeters, 30–40 % infill. The hooks then form with their layer lines running *across* the jaw rather than along the flex, which is the direction a cantilever wants.

Use **PETG, ABS/ASA or nylon** in a cabinet that gets warm. PLA is the wrong material for anything that must hold a spring at 50 °C.

### Scope — read this

This is a **mechanical carrier, not an enclosure rating**. It provides no IP rating, no arc containment, no fire rating and no electrical isolation. Mains work belongs behind proper barriers and a proper enclosure, and none of these materials is certified for any of that by anyone. The hood is a finger and dust cover for low-voltage electronics; it is not a terminal shroud and must not be used as one.

## Verification

Every mode was rendered through the **real** `cq_runner` sandbox at the manifest defaults, at the **min and max of every slider that applies to the mode**, at **every option of every select**, at the **all-min and all-max corners**, and at every declared preset. **61 cases, 61 pass**, each asserted `is_watertight == True`, `body_count == 1`, positive volume and a finite non-degenerate bounding box.

Bounding-box range across the whole sweep:

| Mode | min (mm) | max (mm) |
| :--- | :--- | :--- |
| `rail_carrier` | 44.2 × 25.0 × 15.5 | 127.7 × 124.0 × 45.5 |
| `hat_hood` | 32.0 × 27.0 × 10.0 | 127.7 × 117.7 × 60.0 |
| `riser_frame` | 30.0 × 25.0 × 5.5 | 127.7 × 117.7 × 26.4 |

**Three defects were found by the sweep and fixed. None of them raised an exception, and one of them is the single most deceptive failure this engine has.**

1. **The riser frame's window swallowed its own standoffs — and the result was watertight.** The window was derived from the *plate*; at a large `board_margin` the plate outgrows the hole pattern, so the window grew past the bosses and cut them free. The output was **five bodies — four floating standoffs and a rim — every one of them individually watertight**, so `is_watertight` returned `True` and only the body count caught it. **Watertight is not connected.** The window is now bounded *inside* the standoff ring, derived from `hole_dx`/`hole_dy`, never from the plate.

2. **The hood's bolt bosses landed exactly tangent to its cavity wall.** At the all-min corner the cavity inner face sat at 13.0 mm and the boss surface at 13.0 mm: two coincident faces, 8 non-manifold edges, and a kernel that reported success. The hood's outer size is now derived from the pattern *and its own wall* so the cavity always clears the bosses by 1 mm. Same lesson as the tangent-torus trap: **overlap or clear, never touch.**

3. **A vent slot could run underneath a standoff.** The vent keepout was measured from the *plate edge*, which is the wrong reference — the thing a vent must avoid is the boss pattern. At a large plate margin a slot reached under a boss, leaving a boss sitting over a hole. That is a weak boss and a sliver in the mesh, and nothing in the kernel or the mesh checker objects to it. The vent window is now computed from the pattern, and the slot count is derived from the space that survives it rather than picked first and trimmed afterwards.

Two further mistakes were caught by reading the failures rather than the code: folding `rail_len` into the hood and the frame made two parts that never see a rail grow when the rail length was raised (an ALL-MIN hood 60 mm long from a 25 mm pattern), and the plate size is now derived from the board footprint for every mode and from the rail *only* for the mode that touches one.

The traps that did not bite, because the rules were paid for elsewhere in the commons: every standoff, boss and hook straddles the plate it grows from in Z, so no fuse is tangential; no internal void is sealed (the hood is open at its bottom, the frame through its window, every standoff bore at its top face); and no fillet is taken on any edge a bore or a slot has touched.
