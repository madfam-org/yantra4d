# Lamp Standard Adapter Kit

A **capstone any-to-any lamp-base adapter** that bridges the four dominant
lamp-base families so a bulb built for one fixture drops into another. Generated
with **CadQuery** (B-Rep). It spans the Edison **screw** bases **E26** (North-
American medium) and **E27** (European medium), and the **twist-lock bayonet**
bases **GU10** and **B22/BA22d**. Each mode carries a female receptacle for one
standard and a male base for another, with a wiring channel straight through.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Edison ↔ Edison** | `e26_to_e27` | Female Edison socket (base A) below + male Edison base (base B) above — an E26↔E27 translator (either direction). |
| **Edison ↔ GU10** | `edison_to_gu10` | Female Edison socket below + a GU10 twist-lock puck above — screw into an Edison fixture, carry a GU10 bulb. |
| **GU10 ↔ B22** | `gu10_to_b22` | A GU10 receptacle skirt below + a B22 bayonet base above — bridge the two twist-lock standards. |

## Real base geometry

| Base | Nominal dimensions (mm) |
| :--- | :--- |
| E26 (Edison, 7 TPI) | major Ø 26.05, pitch 3.629 |
| E27 (Edison, 7 TPI) | major Ø 26.40, pitch 3.629 |
| GU10 (bayonet) | shell Ø 26, two Ø4.7 pins on a 10 mm span |
| B22/BA22d (bayonet) | shell Ø 22, two Ø3.0 pins on a 22 mm span |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Base Standards | `edison_a` | E26 | Lower (female) Edison receptacle. |
| Base Standards | `edison_b` | E27 | Upper (male) Edison base. |
| Thread & Fit | `clearance` | 0.4 mm | Per-side printed-thread slop. |
| Thread & Fit | `turns` | 3.0 | Engagement turns (snapped to a half-integer; capped at 3.5). |
| Body | `wall` | 2.4 mm | Shell/skirt wall thickness. |
| Body | `bore` | 12 mm | Central wiring bore (opens both ends). |
| Body | `puck_h` | 22 mm | GU10/B22 twist-lock puck height. |

## Presets

- **E26 to E27 Translator** — the everyday medium-base region converter.
- **Edison Socket to GU10 Bulb** — run a GU10 spot in an Edison fixture.
- **GU10 to B22 Bridge** — cross the two twist-lock standards.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces (this object bridges TWO lamp families):**
  - **Edison Screw Thread** (`thread`, IEC 60061 E26/E27, 7 TPI) — the functional
    Edison thread; **compatible with** `socket-adapter`, `lamp-socket-extender`,
    `lampshade`.
  - **Bayonet Twist-Lock** (`snap`, GU10 / IEC 60061 B22d) — the twist-lock pins
    and skirt; **compatible with** `socket-adapter`.
  - **Central Wiring Bore** (`socket`, internal) — the through-bore for wiring.
- **Material awareness:** `clearance` tunes the printed thread fit per material and
  shrinkage; `tolerance_by_material` is declared.
- **Societal benefit:** the four dominant lamp bases split the world by geography
  and fixture type, so a bulb often will not fit the socket you have. A printed
  any-to-any base adapter lets a household reuse bulbs and fixtures across all four
  standards instead of discarding them.
- **License:** CERN-OHL-W-2.0

## ⚠️ Electrical safety

These adapters sit in **mains-voltage** lighting circuits. A printed plastic
adapter is **not a certified electrical fitting**: FDM plastics can soften with
lamp heat and offer no guaranteed dielectric rating or creepage/clearance
compliance. Treat these parts as **mechanical mock-ups, fit checks, and low-power
LED experiments** — not as a substitute for a listed adapter in a permanent
installation. Never exceed the wattage/heat rating of your filament, keep printed
parts away from hot incandescent/halogen envelopes, and if you are not qualified
to work on mains wiring, don't. Using these parts on a live circuit is **your
responsibility**.

## Thread modeling notes (watertight + fast — four traps avoided)

- Edison threads are **volumetric fused helical ribs**: a trapezoidal profile
  swept along a genuine `makeHelix` path and unioned into the wall, root buried so
  the boolean is a clean fusion (not a fragile tangent kiss).
- **Half-integer turns** (`floor(n)+0.5`): an integer turn count degenerates the
  OCCT helical sweep to a negative-volume / null body.
- **Closed-base sockets:** every female socket has a solid base disk (the bore
  stops below a cap); the wiring channel is bored through the base afterward — an
  open-both-ends bore tessellates non-watertight.
- **No flip-then-attach:** the unflipped socket is already the correct orientation;
  the male base / puck stacks on the closed top, never on an open rim.
- **Turn ceiling 3.5:** a very tall thread on a thin wall can tessellate non-
  watertight even at a half-integer, so turns are capped at the validated ceiling.
  Real lamp bases engage ~2–3 turns, so the cap costs nothing physical.
