# Brick Baseplate

One plate, two grid ecosystems.

A **CadQuery** B-Rep hyperobject — every mode renders watertight and exports STEP. Un hiperobjeto **CadQuery** B-Rep: cada modo es hermético y exporta STEP. Un hyperobjet **CadQuery** B-Rep : chaque mode est étanche et exporte en STEP. Um hiperobjeto **CadQuery** B-Rep: cada modo é estanque e exporta STEP.

Part of the **Yantra4D Hyperobjects Commons** · Official visualizer: [Yantra4D](https://app.yantra4d.com)

## Why this exists

The commons speaks two module grids and has never joined them.

`brick-tile` publishes the **construction-brick grid** — an 8 mm stud pitch with Ø4.8 mm studs and hollow underside clutch tubes — and is the *only* member of that family. Four cartridges publish **Gridfinity's 42 mm module**: `gridfinity`, `gridfinity-baseplate`, `gridfinity-tool`, `grid-hub`, plus `din-rail-clip`'s dock.

A brick model and a Gridfinity drawer are found in exactly the same rooms and have no relationship at all. This plate is that relationship, in **both directions**.

## Modes

| Mode | Label | What it is |
| :--- | :--- | :--- |
| `stud_baseplate` | Stud Baseplate | A plain brick baseplate: studs up, hollow underside with clutch tubes on the same grid |
| `gridfinity_base` | Gridfinity-Footed Baseplate | Brick studs up, Gridfinity **feet** down — a brick surface that sits in a Gridfinity grid |
| `grid_socket_plate` | Gridfinity Socket Plate | Gridfinity baseplate sockets up, brick **clutch tubes** down — Gridfinity bins that sit on a brick surface |

## Both grids come from the cartridges that publish them

| Brick (`brick-tile`) | | Gridfinity (`gridfinity`) | |
| :--- | ---: | :--- | ---: |
| stud pitch | 8.0 mm | cell pitch | 42 mm |
| stud Ø | 4.8 mm | foot taper | 39.2 → 41.5 mm over 5 mm |
| stud height | 1.8 mm | socket taper | 39.2 → 42 mm over 5 mm |
| plate height | 3.2 mm | corner radius | 3.75 mm |
| clutch tube OD / ID | 6.5 / 4.9 mm | | |

**A correction the primary source forced.** The wave plan's slot text specifies "8 mm stud pitch, Ø3.2 mm stud **(verify)**". The 3.2 mm figure is the **plate height**, not the stud: the live cartridge — which is the primary source, and the object this one has to mate — publishes Ø4.8. A 3.2 mm stud would clutch nothing, in this commons or out of it. The plan marked the figure *(verify)* precisely so that this check would happen, and it did.

**Gridfinity governs the footprint, not the brick grid.** In `gridfinity_base` and `grid_socket_plate` the plate size is set by the 42 mm module and the stud grid is fitted *inside* it. A Gridfinity cell that is not 42 mm is not a Gridfinity cell.

## Engine — a measured deviation from the wave plan, recorded rather than quiet

The plan specifies **OpenSCAD** for this slot, on the stated ground that "the Manifold backend is measurably the right kernel per the AGENTS.md CGAL-vs-Manifold note". The OpenSCAD available on this toolchain is **2021.01**, which has **no `--backend` flag at all** — so Manifold is not available and CGAL is what actually runs.

Measured, on the same 16 × 16 baseplate:

| Engine | Time | Result |
| :--- | ---: | :--- |
| OpenSCAD 2021.01 (CGAL) | **9 min 41 s** | reports `Volumes: 2` |
| CadQuery / OCCT | **~11 s** | watertight, `body_count == 1` |

The plan's premise does not hold here, so the cartridge is CadQuery. **The slug, the interfaces, the rank and the ranked order are unchanged** — this is an engine choice, not a substitution. Should a Manifold-capable OpenSCAD become the deployed binary, the case for a `.scad` sibling mode is worth revisiting on evidence.

## Hyperobject Profile

- **Domain:** consumer
- **CDG interfaces:**
  - **Construction Brick Stud Grid** (`grid`, `construction brick 8mm`)
  - **Underside Clutch Tube** (`socket`, same family)
  - **Gridfinity 42 mm Module** (`socket`, `Gridfinity 42 mm`)
- **Measured partners:** **4** — `brick-tile`, `gridfinity`, `gridfinity-baseplate`… in fact `brick-tile`, `din-rail-clip`, `gridfinity`, `locking-mechanism-hyperobject` — verified by running `normalize_family()` and the shipped geometry rules over the live catalog. Exactly the wave plan's count. Closes the `brick-8mm-stud` family.
- **Material awareness:** shrinkage compensation, tolerance-by-material, **and recycled material is enabled** — a baseplate is exactly the kind of large, low-stress object reground filament should be used for.
- **License:** CERN-OHL-W-2.0

## Printing and using it

Print **studs up**, no supports, 4 perimeters, 15–20 % infill. The hollow underside is what keeps a large plate from taking a day to print and from warping as it cools.

A 32 × 32 plate is 256 mm square — the classic large baseplate, and at or past the bed of most printers. The manifest warns at that size and the advice is practical: **print two 16 × 32 plates and clutch them together.** They will hold each other flat better than one warped plate ever will.

Clutch is the whole grip: the studs above only locate, and the **tubes below clutch**. If the plate feels loose on a brick surface, adjust `tube_id` down by 0.1 mm before touching anything else.

### Scope — read this

**Not a toy, and not for a child under three.** This is a printable object with small parts; a printed stud can break off, and a broken stud is a choking hazard. FDM prints also have unsealed layer lines that are difficult to clean properly, and no filament here is certified for mouthing or for food contact. Supervise, inspect before each use, and discard the plate rather than repairing it if a stud shears.

This plate is dimensionally compatible with a widely used construction-brick geometry. It is not affiliated with, endorsed by, or connected to any construction-toy manufacturer.

## Verification

Every mode was rendered through the **real** `cq_runner` sandbox at the manifest defaults, at the **min and max of every slider that applies to the mode**, at **every option of every select**, at the **all-min and all-max corners**, and at every declared preset. **57 cases, 57 pass**, each asserted `is_watertight == True`, `body_count == 1`, positive volume and a finite non-degenerate bounding box. The heaviest case renders a **1.48-million-face** mesh.

Bounding-box range across the whole sweep:

| Mode | min (mm) | max (mm) |
| :--- | :--- | :--- |
| `stud_baseplate` | 16.0 × 16.0 × 3.4 | 256.0 × 256.0 × 16.0 |
| `gridfinity_base` | 41.5 × 41.5 × 8.4 | 251.5 × 251.5 × 21.0 |
| `grid_socket_plate` | 42.0 × 42.0 × 7.4 | 252.0 × 252.0 × 17.0 |

**One finding, and it was in the harness rather than the geometry — which is exactly why it is worth writing down.**

The first sweep reported **21 failures in a row**. Every one after the first said `Broken pipe`. The first said the worker had exited without a reply, on the all-max corner: 1024 studs at Ø6.5 on a 256 mm plate, a 1.5-million-face mesh. The warm CadQuery worker had exhausted itself, and **every subsequent case inherited a dead process** — so a single resource limit read as twenty geometry defects.

Rendered on its own, that same all-max case is **watertight, single-bodied, and correct**. The fix was in the sweep harness, in two parts, and both mirror what production already does: a worker that dies is restarted and *its own case* is reported as a failure rather than silently skipped; and the worker is recycled every eight cases, which is `YANTRA4D_CQ_WORKER_MAX_JOBS` (default 50) at a much lower count because the heaviest cases here are far heavier than an average render. The lesson generalises past this cartridge: **a test harness that lets one failure corrupt the runs after it does not report twenty failures, it reports one failure twenty times** — and the two are indistinguishable unless the harness says which.

The geometry itself was clean from the first render, because the array was treated as the risk it is:

- **Studs and tubes are built as one `pushPoints` extrusion each**, never a loop of unions. A thousand pairwise fuses is a thousand chances to leave a coincident face — and it is also the difference between eleven seconds and several minutes.
- **Every stud and tube straddles the plate it grows from.** `gridfinity`'s own `cup.py` carries the scar that pays for this rule: feet subtracted as *negative* geometry pinched the solid into two volumes meeting at a plane, OpenSCAD reported `Volumes: 2`, and the same construction produced non-manifold edges through OCCT as well. The feet here are positive geometry, unioned with an overlap.
- **The underside cavity is bounded inside the plate by a full wall on every side**, so it can never reach an edge and turn the shell inside out.
- **Nothing is ever sealed**: the cavity opens downward, every clutch tube bore opens downward, every socket opens upward.
