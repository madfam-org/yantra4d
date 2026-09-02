# Busbar Insulating Shroud

The cover over the live metal, on the rail everything else already clips to.

A **CadQuery** B-Rep hyperobject — every mode renders watertight and exports STEP. Un hiperobjeto **CadQuery** B-Rep: cada modo es hermético y exporta STEP. Un hyperobjet **CadQuery** B-Rep : chaque mode est étanche et exporte en STEP. Um hiperobjeto **CadQuery** B-Rep: cada modo é estanque e exporta STEP.

Part of the **Yantra4D Hyperobjects Commons** · Official visualizer: [Yantra4D](https://app.yantra4d.com)

## Why this exists

A control cabinet or a consumer unit is a row of terminals, a comb busbar, and a great deal of exposed conductor between them.

The commons has **seven** cartridges that clip to DIN EN 60715 TS35 rail and **not one that covers anything**. `din-rail-end-stop` terminates the rail. `din-terminal-comb` and `busbar-support` carry the bar. `terminal-cover` covers *one* terminal. The long runs between them stay open — and every one of those runs is a place a hand goes when a board is being worked on live, which is most of the times a board is worked on at all.

## Modes

| Mode | Label | What it is |
| :--- | :--- | :--- |
| `busbar_shroud` | Busbar Shroud | A tunnel over a comb or bar run, **open at both ends** so the conductor continues, closed everywhere a hand is |
| `terminal_shroud` | Terminal Shroud | The same tunnel with lead-out slots in its front face, so conductors leave without the cover coming off |
| `end_barrier` | End Barrier | A flat insulating partition standing between two terminals of different phases or circuits |

All three share the same compliant rail clip back, whose geometry mirrors `din-module`'s published constants exactly.

## The aperture rule, and what it is not

**IEC 60529's IP2X access probe is a Ø12 mm jointed test finger.** Every aperture this cartridge cuts has its minor dimension capped **below** that figure — in the geometry, not in a warning:

```
APERTURE_CAP = 11.0     # applied to the value the geometry uses,
                        # not to the slider
```

That distinction is the whole point. A limit enforced only in the UI is a limit that a preset, a saved configuration or an API call walks straight through. The cap is applied where the number is consumed.

**This is a geometric property of the model. It is not a tested rating, and this cartridge does not claim one.** See the scope note below.

## Hyperobject Profile

- **Domain:** infrastructure
- **CDG interfaces:**
  - **DIN TS35 Rail** (`rail`, `DIN EN 60715 TS35`)
  - **Finger-Safe Aperture** (`pocket`, IEC 60529 IP2X access probe; apertures capped at 11 mm minor dimension)
  - **Compliant Spring Hook** (`snap`, internal)
- **Measured partners:** **7** — `busbar-support`, `devboard-tray`, `din-module`, `din-rail-clip`, `din-relay`, `din-terminal-comb`, `terminal-cover` — verified by running `normalize_family()` and the shipped geometry rules over the live catalog. Exactly the count the wave plan predicted, with no taxonomy caveat.
- **Material awareness:** shrinkage compensation, tolerance-by-material. **Recycled material is deliberately disabled** — a shroud that falls off is worse than no shroud, because it was trusted.
- **License:** CERN-OHL-W-2.0

## Printing and using it

Print **back-plate down**, 4 perimeters, 40 % infill. Do not print this part in PLA: a cabinet in summer reaches temperatures at which PLA loses its spring, and this is a part whose value depends entirely on staying where it was put. **PETG, ABS/ASA or nylon.**

Print several short runs rather than one long one. A run you can lift off in sections is a run someone will actually put back.

Leave room under the roof for the conductor's **bend radius**, not just for the conductor. The manifest warns below 10 mm of covered height, because a conductor forced against the roof of a shroud is a conductor being abraded.

### Scope — read this, it matters more here than on most cartridges

**This is a mechanical and geometric barrier. It carries no electrical rating of any kind.** It has no tested IP rating, no arc rating, no glow-wire or flammability classification, no tracking index, and no dielectric strength figure. The 11 mm aperture cap is a *dimension*, not a certification: IP2X compliance is established by testing a finished product with the specified probe under the specified force, and nothing here has been tested.

It does not make an energised board safe to work on. It is not a substitute for a manufacturer's shroud in an installation that must be certified, and in most jurisdictions a consumer unit must contain listed components only. Isolate the supply and work as a competent person; if you cannot isolate, that is the problem to solve first.

What this part honestly is: a barrier between a hand and a conductor on a board that currently has nothing there at all, printable on the rail that is already installed.

## Verification

Every mode was rendered through the **real** `cq_runner` sandbox at the manifest defaults, at the **min and max of every slider that applies to the mode**, at **every option of every select**, at the **all-min and all-max corners**, and at every declared preset. **57 cases, 57 pass, on the first run**, each asserted `is_watertight == True`, `body_count == 1`, positive volume and a finite non-degenerate bounding box.

Bounding-box range across the whole sweep:

| Mode | min (mm) | max (mm) |
| :--- | :--- | :--- |
| `busbar_shroud` | 44.2 × 10.0 × 19.1 | 52.0 × 120.0 × 80.5 |
| `terminal_shroud` | 44.2 × 10.0 × 19.1 | 52.0 × 120.0 × 80.5 |
| `end_barrier` | 44.2 × 10.0 × 27.5 | 44.2 × 120.0 × 105.5 |

Clean on the first run because five rules were paid for by earlier cartridges in this tranche and applied here before any geometry was written:

- **The tunnel is open at both ends by construction.** A shroud closed at its ends encloses a void, and a sealed void meshes as two bodies however valid the kernel reports the solid — the failure that cost `din-rail-end-stop` a debugging round in this same tranche. Open ends are also correct: a busbar run continues past the cover, which is the whole reason a cover is needed in the middle of it.
- **The body width always contains the rail hooks.** `BODY_W = max(MIN_BODY_W, bar_w + 2·wall + 2)`. A narrower body would sit *between* the hooks, they would touch nothing, and the render would be three separate individually-watertight solids.
- **Every union straddles what it grows from** by a named overlap, so no fuse is tangential.
- **Slot counts are derived from the space that survives the margins**, and dropped entirely when there is none, rather than picked first and trimmed.
- **The `end_barrier` is solid, not shelled**, and its lightening cut-outs are bounded well inside it so a continuous frame always survives — a barrier's job is to be continuous material between two conductors.
