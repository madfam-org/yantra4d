# Lens Filter Step Ring

Adapts one photographic **filter thread** to another, generated with **CadQuery**
(B-Rep). Screw-in filters and lens fronts share a small family of nominal thread
diameters (**M46/M49/M52/M58/M62/M67/M72/M77/M82**) at a fine **0.75 mm** pitch. A
step ring puts a female thread of one size on the bottom and a male thread of
another on top, so a filter made for one diameter fits a lens made for another.
Every thread is a real filter thread, so it mates any filter-thread part.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Step Ring (F→M)** | `step_ring` | Female thread of size A on the bottom (screws onto a lens) → male thread of size B on top (accepts a filter) — the classic step-up / step-down adapter. |
| **Stacking Coupler (F→F)** | `coupler_ring` | Female threads on both faces — screws a male-threaded filter onto each side, stacking two filters back-to-back. |
| **Reverse Ring (M→M)** | `reverse_ring` | Male threads on both faces — threads into a female filter thread on each end (couple a lens filter thread to another). |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Filter Sizes | `thread_a` | M58 | Nominal filter thread on the bottom face. |
| Filter Sizes | `thread_b` | M52 | Nominal filter thread on the top face. |
| Thread & Fit | `thread_turns` | 4.5 | Thread engagement turns per face. |
| Thread & Fit | `clearance` | 0.3 mm | Per-side fit slop on the female threads. |
| Thread & Fit | `wall` | 2.4 mm | Ring side-wall thickness. |
| Thread & Fit | `top_th` | 2.2 mm | Web thickness joining the two sections. |
| Thread & Fit | `grip_teeth` | 0 | Optional vertical grip flutes (0 = off). |

## The thread (why it's a solid of revolution)

Each thread is **cosmetic**: a sawtooth radial profile revolved 360° so male
crests trace the nominal major diameter and the female bore relief traces a
matching minor. **One revolve per thread** — no per-turn helical booleans — is
fast and inherently watertight, the right idiom for a light, quick-screwing
filter thread. (A true `makeHelix` sweep at these 23–41 mm radii is both far
slower and prone to severed, non-watertight bodies here, so the shipped
`lens-cap` cartridge uses this same cosmetic idiom.) The central light bore is a
through-hole that vents both ends — no trapped voids.

## Presets

- **58→52 Step-Down** — the most common step-down for a 52 mm filter on a 58 mm lens.
- **77↔77 Stacking Coupler** — stack two 77 mm filters back-to-back.
- **52↔58 Reverse Ring** — a double-male reverse adapter.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **Filter Thread** (`thread`, *M46-M82 x 0.75*) — the filter thread on each
    face, defined by `thread_a`, `thread_b`, `thread_turns`, `clearance`.
    **Mates:** [`lens-cap`](../../lens-cap/) (its snap cap and step ring share the
    same filter-thread family).
- **Material awareness:** `tolerance_by_material` is declared — the thread
  clearance is exposed so the screw fit tunes per material/printer.
- **Societal benefit:** every photographer accumulates filters and lenses in
  mismatched thread sizes and a wallet of proprietary step rings. A printable
  step ring lets someone make the exact adapter a shot needs, reuse an expensive
  filter across every lens, and replace a lost ring in the field. It is a
  companion for the filter-thread family.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via a `PARAM(lambda: name, default)`
  guard; `target_part` dispatches the part; the final solid is `result`.
- Threads are serrated solids of revolution (never boolean-cut grooves or slow
  helical sweeps); the light bore is a through-hole (vented); a final `.clean()`
  is wrapped in try/except. All shipped modes, all nine sizes and the
  extreme-parameter cases render **watertight**, single-body, in about 1 s.
