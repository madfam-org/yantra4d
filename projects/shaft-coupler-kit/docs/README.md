# Shaft Coupler Kit

A **capstone any-to-any shaft coupler** that bridges every common small-shaft
profile so a motor, knob, encoder or hand crank built for one shaft drives
another. Generated with **CadQuery** (B-Rep). The user measures each shaft and
picks its bore — **round**, **single-D flat**, or **hex** — at the **3/4/5/6/8 mm**
sizes that dominate hobby and appliance drivetrains. Because each end is
selectable independently, one part couples a 5 mm D motor shaft to a 6 mm round
encoder, or a 1/4 in hex bit to a round pot.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Rigid Coupler** | `rigid_coupler` | A barrel with a selectable bore at each end (A below, B above) and a solid mid web — joins two shafts end-to-end. |
| **Bore Adapter Sleeve** | `bore_adapter` | A plain-cylinder sleeve that seats in a larger round bore and carries a smaller selectable bore inside — steps a big hole down to a small shaft. |
| **Set-Screw Hub** | `set_hub` | A hub/collar with one selectable bore, a radial set-screw, and an optional 4-hole flange bolt circle so a wheel/gear/arm bolts on. |

## Real shaft geometry

Common shaft diameters: **3.0, 4.0, 5.0, 6.0, 8.0 mm** (and 6.35 mm / 1⁄4 in for
hex bits). D-flat depth is ~0.5 mm on small shafts; hex is measured **across-flats
(AF)**. The `set_hub` flange bolt circle is exposed so it mates the `spline-hub`
flange family.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Shaft Bores | `bore_a` | round | Bore A profile: round / D-flat / hex. |
| Shaft Bores | `bore_b` | D-flat | Bore B profile (rigid coupler upper end). |
| Shaft Bores | `shaft_a` | 5 mm | Shaft A Ø (round/D) or across-flats (hex). |
| Shaft Bores | `shaft_b` | 6 mm | Shaft B Ø, or the host-bore Ø the sleeve plugs into. |
| Shaft Bores | `flat_depth` | 0.5 mm | D-flat chord depth from the shaft wall. |
| Body | `body_len` | 24 mm | Total length along the shaft axis. |
| Body | `wall` | 3 mm | Radial wall around the largest bore. |
| Hardware | `setscrew` | on | Radial set-screw clearance hole(s). |
| Hardware | `setscrew_dia` | 3.2 mm | Set-screw clearance (~M3). |
| Hardware | `bolt_circle` | 0 mm | Flange bolt-circle Ø (`set_hub`; 0 = no flange). |

## Presets

- **5 mm D to 6 mm Round** — the everyday motor-to-encoder coupler.
- **8 mm Bore to Hex Insert** — step a big bore down to a hex driver.
- **Flanged D-Shaft Hub** — bolt a wheel or gear onto a D-shaft.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces (this object bridges the shaft-spline family on two bores):**
  - **Shaft Bore A** (`socket`, 3-8 mm shaft round/D-flat/hex) — the lower/inner
    bore; **compatible with** `knob-dshaft`, `spline-hub`, `shaft-coupler`,
    `servo-horn`.
  - **Shaft Bore B** (`socket`, 3-8 mm shaft round/D-flat/hex) — the upper bore of
    the rigid coupler; **compatible with** `knob-dshaft`, `spline-hub`,
    `shaft-coupler`, `servo-horn`.
  - **Flange Bolt Circle** (`bolt_pattern`, internal) — the `set_hub` flange;
    **compatible with** `spline-hub`.
- **Material awareness:** the 0.2 mm print clearance plus `flat_depth` let the bore
  fit be tuned per material; `tolerance_by_material` is declared.
- **Societal benefit:** small drivetrains are a Tower of Babel of shaft profiles,
  and a mismatch normally means an expensive machined coupler or abandoning a
  repair. A printable any-to-any coupler with independently selectable round/D/hex
  bores lets a maker join whatever two shafts they have, keeping motors, knobs and
  appliances in service.
- **License:** CERN-OHL-W-2.0

## Geometry notes (watertight + fast)

- **Thread-free by design** — every bore is a plain solid cutter, so each render is
  fast and robust.
- Bores extend **past the faces they open on** (vent to a face → no trapped void).
- The rigid coupler keeps a **solid mid web** so the two bores never break through
  into one another — no severed body.
- Hex bores are cut across-corners = AF ⁄ cos 30°; D-flats subtract the outboard
  sliver so the chord sits `flat_depth` in from the wall.
- Chamfers/fillets touch clean blanks only, wrapped in `try/except`.

## Print notes

- Print **bore-axis vertical** for the roundest bores, or split long couplers.
- The set-screw seats best against a **flat** (D or hex); on a round shaft, add a
  dab of thread-lock or file a small flat for the screw to bite.
