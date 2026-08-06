# Drum / Cymbal Sleeve & Wingnut

Tension-rod and cymbal hardware, generated with **CadQuery** (B-Rep). The
functional interface is the drum **tension-rod thread** — the near-universal
**12-24** (major 5.49 mm, 24 TPI, pitch 1.058 mm) on American/Asian kits, or
**M5** (DW/PDP).

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Wingnut** | `wingnut` | A female-threaded wingnut for cymbal-stand tilters and hi-hat clutches — an internal helical thread plus two finger wings. |
| **Tension Rod** | `tension_rod` | A printed tension rod — a **full-length male-threaded** shaft under a flanged head with a 7 mm square drum-key drive. |
| **Cymbal Sleeve** | `cymbal_sleeve` | A smooth stepped sleeve (no thread) with a felt-seat flange that isolates the cymbal bell from the metal rod. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Thread | `thread_std` | `12-24` | 12-24 UNC (US/Asian) or M5 (DW/PDP). |
| Thread | `clearance` | 0.35 mm | Per-side printed-thread fit slop. |
| Rod | `rod_len` | 42.0 mm | Threaded length below the head. |
| Sleeve | `sleeve_len` | 40.0 mm | Sleeve length up the stand post. |
| Sleeve | `post_d` | 6.0 mm | Stand-post clearance bore (6 or 8 mm). |
| Body | `wall` | 3.0 mm | Hub / head / sleeve wall. |
| Rod | `sq_drive` | 7.0 mm | Square drum-key drive across flats. |

## The tension-rod thread (the standard)

Almost every drum tension rod is **12-24 UNC** — 0.216 in (5.49 mm) major
diameter, 24 threads per inch, **pitch 1.058 mm** — with DW and PDP the notable
**M5** exception. The wingnut carries the female thread; the tension rod is a
full-length male thread that screws into the lug and is turned by a **7 mm square
drum key**. The cymbal sleeve is smooth — its whole job is to keep the metal rod
off the cymbal bell — with a wide flange to seat the felt.

## Watertight thread technique

Threads are swept along a **real-radius** `makeHelix` (a near-zero-radius helix
is degenerate) with `makeSolid=True`:

- **Female thread** (wingnut) — an inward trapezoidal rib **unioned** into the
  bore; the hub + wings are built first and the thread is fused **last**, so the
  wing join never fragments the fine thread mesh.
- **Male thread** (rod) — a helical groove **cut** from a solid rod at the crest
  radius. Subtractive threading is watertight at **any** length (a full ~40-75
  turn rod), where an additive outward rib leaves an unsealed spiral crest.
- The turn count is snapped to a **half-integer** (`floor(n)+0.5`) — an integer
  turn count degenerates the OCCT helical sweep into a null/negative-volume body.
- The thread crest is left **flat** (≥ 0.12·pitch) so the STL never tessellates a
  knife edge into separated shells.

## Presets

- **12-24 Wingnut** — the standard cymbal-tilter / clutch wingnut.
- **12-24 Tension Rod** — a full-length threaded rod with a 7 mm key drive.
- **8 mm Cymbal Sleeve** — a felt-seat sleeve for an 8 mm stand post.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interface:** **Tension-Rod Thread** (`thread`, *12-24 UNC 5.49 mm 24 TPI /
  M5*) — the helical thread, defined by `thread_std`, `clearance`, `rod_len`.
  Wingnuts and rods on the same standard mate.
- **Material awareness:** `tolerance_by_material` is declared — `clearance` is
  exposed so the printed-thread fit tunes per material/printer.
- **Societal benefit:** tension rods, wingnuts and cymbal sleeves strip, rust and
  vanish, and one missing 12-24 rod sidelines a drum; a printed part keeps a kit
  playable from parts a drummer makes at home.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via a `PARAM(lambda: name, default)`
  guard; `target_part` dispatches the part; the final solid is `result`.
- All bores are **through-holes** (vented); the square key socket is a blind cut
  open at the top; the thread techniques above keep every mode + extreme
  **watertight**, single-body.
