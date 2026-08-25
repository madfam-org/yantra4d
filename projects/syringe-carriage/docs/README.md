# Syringe Pump Carriage

The carriage set for a DIY lab syringe pump: a barrel clamp, a leadscrew-driven plunger pusher with a **real threaded drive nut**, and a barrel retainer block. Sized to standard Luer syringe barrels and common T8 / M8 leadscrews. A new lab/maker family/cluster.

> **Not an infusion device.** A research / teaching build aid only. Do **not** use for patient infusion.

## Parts / Modos

| Mode | Part | What it is |
|------|------|------------|
| `barrel_clamp` | Barrel Clamp | Saddle block that cradles the syringe barrel and bolts to the pump bed. |
| `plunger_pusher` | Plunger Pusher | Leadscrew carriage with a threaded drive nut and a slot that captures the plunger flange. |
| `barrel_block` | Barrel Retainer Block | Retainer with a barrel bore and a drop-in flange slot to fix the barrel end. |

## Standards & dimensions

- **Luer syringe barrel Ø (BD / Terumo):** 1 mL ~6.6, 3 mL ~9.7, 5 mL ~12.5, 10 mL ~15.9, 20 mL ~20.1 mm.
- **Leadscrews:** T8 trapezoidal (major Ø 8, lead 8, pitch 2) and M8 metric (major Ø 8, pitch 1.25) — the common 3D-printer / pump leadscrews.
- **Nut thread:** true pitch, a volumetric helical rib fused into the bore (not cut grooves), engagement fixed at 3.5 turns (a half-integer) for a well-conditioned printable thread.

## Parameters

- `syringe` — `1mL` / `3mL` / `5mL` / `10mL` / `20mL` (sets barrel channel / bore Ø).
- `leadscrew` — `T8` or `M8` (plunger-pusher drive nut).
- `clearance` (0.15–0.8 mm/side) — barrel channel + nut bore fit.
- `block_w` (24–70 mm) — carriage width across the mounting bolts.
- `mount_bolt` (3–6.5 mm) — frame mounting through-hole (4.4 = M4 clearance).

## Printing notes / Notas de impresión

**EN:** Print the plunger pusher with the nut axis horizontal (or split-print), solid / high-infill for drive stiffness. Start clearance at 0.35 mm and tune to your printer and leadscrew. Bench/teaching aid — not a certified infusion pump.

**ES:** Imprime el empujador con el eje de la tuerca horizontal (o imprímelo en partes), sólido / alto relleno para rigidez del accionamiento. Empieza con holgura de 0.35 mm y ajústalo a tu impresora y husillo. Ayuda de mesa/enseñanza — no una bomba de infusión certificada.

## Hyperobject Profile

- **Domain:** medical
- **CDG interfaces:**
  - **Syringe Barrel Socket** (`socket`, `Luer syringe barrel (1/3/5/10/20 mL)`) — defined by `syringe`, `clearance`.
  - **Leadscrew Drive Nut** (`thread`, `T8 trapezoidal / M8 metric leadscrew`) — defined by `leadscrew`, `clearance`.
- **Material awareness:** `shrinkage_compensation` + `tolerance_by_material` declared — barrel channel and nut bore add user clearance per side.
- **Societal benefit:** open syringe-pump hardware for teaching labs and low-resource research — precise fluid dosing on standard syringes and leadscrews, printed on demand.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via `PARAM(lambda: name, default)`; final solid assigned to `result`; dispatch on `target_part`.
- The nut thread is a fused helical rib; barrel channel and bores open to a face, so every output is **watertight, single-body**.
