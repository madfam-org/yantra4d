# Fermentation Airlock Grommet & Fitting

The gas-management interface of a fermenter, generated with CadQuery (B-Rep).
Three parts share one CDG interface — the carboy/bucket bore.

## Modes

| Mode | `target_part` | What it makes |
| --- | --- | --- |
| **Grommet** | `grommet` | A double-flanged snap-in grommet: a waist sized to the bore, a top flange, and a bottom retaining bead. The groove between snaps over a drilled lid; a stepped through-hole grips the airlock stem. |
| **Airlock Body** | `airlock_body` | A simple printable bubbler: a twin-wall cup with a central inlet standpipe rising into an open outer moat, plus a bottom spigot that plugs the grommet. Prints support-free; holds a CO2 water seal. |
| **Blow-off Adapter** | `blowoff_adapter` | Seats in the grommet like the stem, then steps up to a ribbed hose barb for a blow-off tube during vigorous fermentation. |

## Key parameters

- **Bucket / Carboy Bore (mm)** — the drilled hole the grommet seats into.
- **Airlock Stem OD (mm)** — stem the grommet grips (shared across all parts).
- **Wall Thickness (mm)** — body wall.
- **Flange Diameter (mm)** — top flange that rests on the lid.
- **Lid Thickness (mm)** — snap-groove width = thickness of the lid it clips into.
- **Hose Barb OD (mm)** — blow-off barb outer diameter.

## Geometry notes

Solids with pockets **cut** in. The grommet's retaining bead is a revolved
profile fused volumetrically (like the reference cup-lid grip bead). The bubbler
moat and the central channel are both **open at the top**, so no cavity is ever
sealed into a void — verified across all modes with **zero negative-volume
bodies**. Rim fillets are applied to the clean blank before through-holes are
cut. All three modes are distinct.

## Printing

- The **airlock body** prints upright, moat-up, no supports. Fill the moat with
  sanitized water/vodka to form the CO2 seal.
- The **grommet** prints best in a flexible filament (TPU) for a real seal; PLA
  works if the bore fit is dialled in with the clearance parameter.

## Food-contact responsibility

This part contacts fermenting must and CO2. Geometry only — food-safe/food-grade
filament, thorough sanitation, and achieving an actual gas/liquid seal are the
maker's responsibility. An FDM print is porous; verify it holds a seal before
trusting a batch to it.

## License

Open hardware under **CERN-OHL-W-2.0**. Part of the Yantra4D Hyperobject Commons.
