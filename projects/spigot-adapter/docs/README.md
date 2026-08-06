# 5/8in Spigot Adapter

The light-stand spigot (**"baby pin"**), generated with **CadQuery** (B-Rep): a
**5/8" (16 mm)** cylindrical stud that drops into the receiver on every
photographic light stand, C-stand and grip head. Build a 5/8" spigot to a
1/4-20 thread, to a 3/8-16 thread, or a double-ended spigot.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **5/8" Spigot → 1/4-20** | `spigot_to_quarter` | A wrench hub with a 5/8" baby-pin stud below and a 1/4-20 thread above (male stud or female socket). |
| **5/8" Spigot → 3/8-16** | `spigot_to_three_eighth` | The same adapter with the larger 3/8-16 studio/grip thread. |
| **Double Spigot** | `double_spigot` | A hub with a 5/8" baby-pin stud on **both** ends — stack two stand receivers or a receiver and a grip head. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| 5/8" Spigot | `spigot_d` | 16.0 mm | Baby-pin stud diameter (5/8" = 15.875 mm). |
| 5/8" Spigot | `spigot_len` | 22.0 mm | Stud protrusion length. |
| 5/8" Spigot | `groove_depth` / `groove_pos` | 1.5 / 9.0 mm | Locking-groove depth and height. |
| Hub | `hub_d` / `hub_h` | 22.0 / 12.0 mm | Central hub across-corners size and height. |
| Hub | `hub_shape` | hex | Hex wrench flat, or round. |
| Screw Thread | `thread_len` | 10.0 mm | Male stud length or female socket depth. |
| Screw Thread | `thread_form` | stud | Male stud or female socket. |
| Screw Thread | `thread_style` | cosmetic | Cosmetic threaded envelope, or smooth (tap/insert). |
| Screw Thread | `chamfer_lead` | on | Lead-in chamfers on stud and thread tips. |

## The spigot (why it locks)

The 5/8" baby pin is a plain cylindrical stud with an **annular locking groove**
partway up. It drops into a stand's receiver, and the stand's set-screw seats
into the groove to lock it against pull-out and rotation. The receiver end of
the adapter carries a real **UNC screw thread** — 1/4-20 or 3/8-16 — as a male
stud (screws into a device) or a female socket (a screw goes in). The groove is
an open annular relief (vents to outside), and a female socket is bored to a
clamped depth so it never breaches the far face.

## Presets

- **5/8" → 1/4-20 Stud** — the classic stud-to-camera-screw adapter.
- **5/8" → 3/8-16 Stud** — stud to the larger studio thread.
- **5/8" → 3/8-16 Socket** — a receiver end instead of a male stud.
- **Double 5/8" Spigot** — a stud on each end for stacking.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **5/8in Baby Pin** (`socket`, *5/8in (16mm) baby pin*) — the spigot stud and
    groove, defined by `spigot_d`, `spigot_len`, `groove_depth`, `groove_pos`.
    Any stud built to 5/8" drops into every baby-pin receiver.
  - **1/4-20 / 3/8-16 Thread** (`thread`, *ASME B1.1 1/4-20 & 3/8-16 UNC*) — the
    screw interface, defined by `thread_len`, `thread_form`, `thread_style`, for
    the studio/camera threads.
- **Material awareness:** `tolerance_by_material` is declared — stud and thread
  dimensions are exposed so the fit tunes per material/printer.
- **Societal benefit:** the 5/8" baby pin is the universal grip and lighting
  interface; on-demand spigot adapters let a crew mate any light or accessory to
  any stand from printed parts and replace a stripped or lost spigot on set.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via a `PARAM(lambda: name, default)`
  guard; `target_part` dispatches the part; the final solid is `result`.
- The stud, threads and hub are solids of revolution and overlapping cylinders;
  threads are cosmetic (one `revolve` each, no per-turn booleans). The locking
  groove is an open annular cut and the female socket depth is clamped, so no
  trapped voids form. All shipped modes and presets render **watertight** in
  well under 20 s.
