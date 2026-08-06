# 1/4-20 Camera / Tripod Interface

The universal camera/tripod **1/4"-20 UNC** screw interface, generated with
**CadQuery** (B-Rep) — the base every camera mount, plate, cage, arm, and adapter
bolts onto. Pick a male stud, a female socket, or the ubiquitous 1/4-to-3/8
adapter, on a configurable disc or plate base.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Stud (Male)** | `stud` | A 1/4-20 male boss on a base — the classic tripod / quick-plate screw stud. |
| **Socket (Female)** | `socket` | A base plate/block with a 1/4-20 female hole — the receiver for mounts, plates, adapters. |
| **1/4-to-3/8 Adapter** | `adapter` | A short body with a 1/4-20 socket on the bottom face and a selectable 1/4-20 **or** 3/8-16 stud on top. |

## Thread standard (nominal envelope)

Both threads are modelled at the correct UNC nominal envelope so the interface is
dimensionally real (verified against rendered geometry):

| Thread | Major dia | TPI | Pitch | Pitch dia | Minor dia |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1/4"-20 UNC** | 6.35 mm (0.25") | 20 | 1.27 mm | 5.524 mm | 4.976 mm |
| **3/8"-16 UNC** | 9.525 mm (0.375") | 16 | 1.5875 mm | 8.491 mm | 7.749 mm |

### Thread styles (`thread_style`)

| Style | What it builds | Use it for |
| :--- | :--- | :--- |
| **Cosmetic** *(default)* | A single revolved sawtooth solid of revolution — crests at the correct major diameter, roots at the minor diameter. Fast and watertight. | Preview, quick prints, snap-fit mock-ups. |
| **Smooth** | A plain **pitch-diameter** cylinder (stud) or hole (socket): ~5.5 mm for 1/4-20, ~8.5 mm for 3/8-16. | Tapping a real thread, or a heat-set insert. |
| **Real** | A true swept UNC helix unioned onto a minor-diameter core. **Slower** (opt-in). | A directly-printable functional thread. |

> The default is deliberately fast: the cosmetic envelope is a single `revolve`
> (no per-ring booleans), so render cost is dominated by the CadQuery cold-start,
> not the geometry. `ring_count` caps the tooth count on long studs.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Interface | `target_part` | `stud` | `stud` / `socket` / `adapter`. |
| Interface | `adapter_top` | `3/8-16` | Adapter top thread: `3/8-16` or `1/4-20` (bottom is always a 1/4-20 socket). |
| Thread | `thread_style` | `cosmetic` | `cosmetic` / `smooth` / `real`. |
| Thread | `thread_len` | 8.0 mm | Stud height, or socket depth (clamped so it never breaches the base). |
| Thread | `chamfer_lead` | on | Lead-in chamfer at the thread start / socket mouth. |
| Thread | `ring_count` | 10 | Cosmetic thread tooth count (advanced; ignored for smooth/real). |
| Base | `base_shape` | `disc` | `disc` or rounded `square`. |
| Base | `base_size` | 25 mm | Disc diameter or square side. |
| Base | `base_thick` | 4.0 mm | Base plate / body thickness. |

## Presets

- **Tripod Quick-Plate Screw** — a 25 mm disc carrying an 8 mm 1/4-20 stud.
- **Camera Mount Socket Plate** — a 40 mm square, 8 mm thick, with a 1/4-20 socket.
- **1/4-to-3/8 Adapter** — the classic 16 mm adapter: 1/4-20 socket below, 3/8-16 stud above.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **1/4-20 UNC Camera Thread** (`thread`, *ASME B1.1 1/4-20 UNC*) — the primary
    interface, present on every mode, defined by `target_part`, `thread_style`,
    `thread_len`, `chamfer_lead`. Any part built here mates with the global
    installed base of tripods, plates, and cages.
  - **3/8-16 UNC Tripod Thread** (`thread`, *ASME B1.1 3/8-16 UNC*) — the heavy
    tripod-head interface, exposed on the adapter's top face via `adapter_top`.
- **Material awareness:** clearances are declared tunable per material
  (`tolerance_by_material`); the socket hole is cut at a tapping-oriented envelope
  so a real screw can bite the printed wall.
- **Societal benefit:** 1/4-20 is the single most common mechanical interface in
  photography and video. An open, printable base for the thread lets anyone build
  mounts and 1/4-to-3/8 adapters on demand instead of buying single-purpose parts.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- All modes, thread styles, and shipped presets render **watertight**; the
  parametric extremes (min and max of every slider) were verified watertight too.
