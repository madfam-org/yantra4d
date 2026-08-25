# Sharps Container Lid

Turns any bucket, jar, or carboy into a sharps container. Generated with
**CadQuery** (B-Rep). A press-on lid with a **one-way baffle**: the drop slot is
offset from the internal chute mouth, so a needle goes in and cannot be shaken,
tipped, or fished back out.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

> **This is a printable HARM-REDUCTION aid, not a certified FDA/NOM sharps
> container.** It does not replace regulated clinical waste handling. Use it where
> the regulated option is genuinely unavailable, and dispose of the sealed
> container through a proper waste stream.

## Why this cartridge exists

Medical was thin in the commons and clinic-waste safety was unrepresented.
Needlestick injury is a preventable harm whose barrier is almost never knowledge —
it is that a certified bin is unavailable, unaffordable, or simply not where the
injection happens. Diabetics, veterinary and field clinics, and harm-reduction
programs improvise with soda bottles a needle can be shaken back out of. This lid
reuses the **existing bucket/carboy bore series** already in the commons, so it
fits a vessel people already have.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Baffle Lid** | `baffle_lid` | Press-on lid with the offset one-way chute and hub slot. |
| **Screw Baffle Lid** | `screw_lid` | The same baffle on a coarse thread, for a threaded carboy. |
| **Closure Cap** | `closure_cap` | A plain solid cap that seals a FULL container before disposal. |

The closure cap is the second half of the safety story: a container that can be
filled but not sealed is only half a solution.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Vessel | `bore_dia` | 95.0 mm | Vessel mouth outer diameter — the shared bucket/carboy series. |
| Vessel | `clearance` | 0.4 mm | Per-side press-fit gap. |
| Vessel | `wall` | 2.6 mm | Skirt wall thickness. |
| Vessel | `skirt_h` | 14.0 mm | How far the skirt grips down the vessel. |
| Vessel | `top_th` | 3.2 mm | Top plate thickness — a needle must not push through it. |
| Baffle | `slot_w` | 22.0 mm | Drop-slot width. |
| Baffle | `slot_l` | 30.0 mm | Drop-slot length. |
| Baffle | `chute_off` | 16.0 mm | **The one-way trick** — offset between slot and chute mouth. |
| Baffle | `chute_h` | 22.0 mm | Internal chute depth. |
| Hub | `hub_dia` | 7.6 mm | Needle-hub diameter (a Luer hub is about 7.5 mm). |
| Vessel | `thread_pitch` | 6.0 mm | Coarse thread pitch (screw lid only). |

The **needle-hub slot** in the top face lets a syringe hub be twisted off and
dropped without the user touching the needle, and it is placed on the far side
from the drop slot so a hub twist-off never lands over the open chute. It is
parameterised on hub diameter, not on any one syringe brand.

## Presets

- **5-Gallon Bucket (Clinic)** — the common clinic vessel.
- **Small Jar (Home Injector)** — for personal use.
- **Threaded Carboy** — the screw-lid variant.
- **Seal When Full** — the closure cap.

## Hyperobject Profile

- **Domain:** medical
- **CDG interfaces:**
  - **Bucket / Carboy Bore Series** (`socket`) — `bore_dia`, `clearance`, `wall`,
    `skirt_h`. The existing commons vessel-bore interface, compatible with
    `cup-lid` and `jar-adapter`.
  - **One-Way Baffle Profile** (`profile`, internal) — `slot_w`, `slot_l`,
    `chute_off`, `chute_h`, `top_th`.
  - **Needle Hub Slot** (`pocket`, Luer hub nominal Ø 7.5 mm) — `hub_dia`, `top_th`.
- **Material awareness:** `clearance` and `wall` are exposed for per-printer
  tuning; `tolerance_by_material` is declared.
- **Societal benefit:** turns a container people already have into a safer one,
  where the regulated option is not available.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard; the final solid is assigned to `result`.
- **Watertight strategy:** the lid is one extruded solid. The skirt is a single
  annular cut; the chute is a solid tube **unioned into the underside before its
  own bore is cut**, so the baffle never floats; the drop slot and hub slot are
  full-depth cuts through the top plate only. The slot is clamped to keep a real
  land at the rim, and the baffle offset is capped by the room remaining, so the
  chute can never intersect the skirt wall at any parameter extreme.
- The chute solid extrudes a real distance **into** the top plate rather than
  stopping flush with its underside. A flush union is not a union: OCCT reports
  two solids and the mesh exports as a chute floating inside the lid. The chute
  bore, by contrast, deliberately **stops at the plate underside** — the drop slot
  overlaps the chute mouth in plan, so the slot alone breaches the plate. Carrying
  the bore up through the plate as well would open a second, straight-down hole
  directly over the chute, which is exactly the shake-back-out path the offset
  baffle exists to prevent. A section scan of the shipped default confirms the
  plate is solid above the chute and open only at the offset slot.
- All shipped presets, defaults, **and the minimum/maximum of every parameter**
  render **watertight** (single body).
