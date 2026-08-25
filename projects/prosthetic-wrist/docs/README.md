# Prosthetic Wrist Adapter

A quick-disconnect wrist unit for upper-limb prostheses on the open **e-NABLE / Open Source Leg 4-bolt** terminal interface. Grows the `enable-prosthetic` family — mates the `prosthetic-socket` distal adapter.

> **Not a medical device.** This is a fabrication blank. A clinician / occupational therapist / prosthetist must measure, fit and approve any prosthesis before use. Fit is user-specific.

## Parts / Modos

| Mode | Part | What it is |
|------|------|------------|
| `wrist_plate` | Wrist Plate | 4-bolt flange to the socket with a keyed quick-disconnect socket on the outer face. |
| `terminal_puck` | Terminal Puck | Mating coupler with its own 4-bolt pattern and a keyed post that locks into the wrist plate. |
| `wrist_flexion` | Fixed-Flexion Block | Two 4-bolt flanges joined by a solid wedge to set the terminal device at a wrist angle. |

## Standards & dimensions

- **Terminal interface:** e-NABLE / OSL 4-bolt — four bolts on a square pattern on a ~40 mm bolt circle, M5 (5.5 mm clearance). Same distal adapter `prosthetic-socket` exposes.
- **Quick-disconnect:** a keyed (D-profile) cylinder so the terminal device seats without rotating; the puck post is printed under the socket by a fixed clearance.

## Parameters

- `plate_dia` (40–90 mm) — outer diameter of the 4-bolt flange.
- `bolt_circle_dia` (20–80 mm) — pitch circle of the 4-bolt pattern (e-NABLE / OSL ~40 mm).
- `bolt_dia` (3–8 mm) — through-hole for the mounting bolts (5.5 = M5 clearance).
- `plate_th` (5–16 mm) — flange thickness; carries the wrist load.
- `disc_dia` (14–34 mm) — keyed quick-disconnect socket / post diameter.
- `flex_angle` (0–45°) — fixed wrist flexion angle between the two flanges.

## Printing notes / Notas de impresión

**EN:** Print load-bearing wrist parts solid or high-infill in PETG / PA and orient bolt holes vertical. Tune `bolt_dia` to your fasteners. An occupational therapist or prosthetist must approve the assembly before use.

**ES:** Imprime las piezas de muñeca que soportan carga sólidas o de alto relleno en PETG / PA y orienta los agujeros de pernos verticales. Ajusta `bolt_dia` a tus tornillos. Un terapeuta ocupacional o protesista debe aprobar el ensamble antes de usarlo.

## Hyperobject Profile

- **Domain:** medical
- **CDG interfaces:**
  - **e-NABLE / OSL 4-Bolt Terminal** (`bolt_pattern`, `e-NABLE / OSL 4-bolt`) — defined by `bolt_circle_dia`, `bolt_dia`, `plate_dia`. **compatible_with:** `prosthetic-socket`.
  - **Keyed Quick-Disconnect** (`socket`, `internal`) — defined by `disc_dia`.
- **Material awareness:** `shrinkage_compensation` + `tolerance_by_material` declared — the keyed post is printed under the socket by a fixed clearance.
- **Societal benefit:** swap hands and tools in seconds on the open e-NABLE interface, printed locally for a fraction of clinical cost, interoperable across the humanitarian-prosthetics commons.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via `PARAM(lambda: name, default)`; final solid assigned to `result`; dispatch on `target_part`.
- Bolt patterns use fillet-before-cut; the flexion block seats the tilted flange with a deep column overlap so it stays **watertight, single-body** at every angle 0–45°.
