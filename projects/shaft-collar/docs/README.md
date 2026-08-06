# Keyed Shaft Collar / Collar de Eje

A **shaft collar** clamps onto a round drive shaft to set an axial stop, space a
bearing, or lock a hub, generated with **CadQuery** (B-Rep). Build a solid
**setscrew collar**, a **split clamp collar** that squeezes shut without marring
the shaft, or a **flanged shaft stop** with a wide seating face. Sized to the
common **6-12 mm** small-shaft range that the `shaft-spline` commons family shares.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

---

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Setscrew Collar** | `setscrew_collar` | Solid ring with a single radial setscrew bore that threads down onto the shaft to pin the collar in place. |
| **Clamp Collar (Split)** | `clamp_collar` | A ring with a saw slit cut fully through one wall and a cross clamp-bolt bore; tightening squeezes the ring shut around the shaft without marring it. |
| **Flanged Shaft Stop** | `shaft_stop` | A set collar with a wide coaxial base flange that presents a large face for a bearing or panel to seat against. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Shaft & Ring | `bore_d` | 8.0 mm | Shaft bore Ø. shaft-spline commons range 6-12 mm. |
| Shaft & Ring | `wall` | 5.0 mm | Radial ring wall around the bore. |
| Shaft & Ring | `collar_h` | 10.0 mm | Collar height along the shaft axis. |
| Fixing | `set_d` | 4.3 mm | Setscrew / clamp-bolt clearance (M4 ~4.3 mm). |
| Flange | `flange_ext` | 6.0 mm | Flange radial extension past the ring OD (`shaft_stop`). |
| Flange | `flange_t` | 3.0 mm | Flange thickness (`shaft_stop`). |

## Why these dimensions

Small drive shafts on motors, encoders, hobby gearboxes and 3D-printer hardware
cluster in the **6-12 mm** range — the same bore range the rest of the shaft-spline
commons keys to, so a collar and a `spline-hub` or D-shaft knob share one shaft. A
radial **M4 (~4.3 mm)** setscrew is the standard fixing for this size (M3-M5 span the
range); the split clamp collar reuses that same bolt across the gap. A stiff
printable ring wants roughly a **5 mm** wall so the setscrew has material to bite.

## Watertightness

Every collar starts as a **solid OD cylinder** with the shaft bore cut fully
**through** it, so the bore vents to both faces — never a sealed cavity. The top OD
rim is filleted on the **clean ring blank BEFORE** any feature is cut. Setscrew and
clamp-bolt holes are **through-bores** that vent to outside. The split collar's saw
slit is a thin box cut fully through one wall, opening bore→OD as a **genuine gap**
(not a trapped void). The flanged stop **unions** a coaxial disk into the ring's
shared material and bores the shaft through the whole stack, yielding one manifold
body. Validated watertight with `body_count == 1` across all three modes plus the
minimum and maximum parameter extremes.

## Presets

- **8 mm Setscrew Collar** — the common mid-range shaft at spec.
- **10 mm Split Clamp Collar** — a shaft-friendly clamping stop.
- **6 mm Flanged Stop** — a small-shaft thrust stop with a wide seat.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **6-12 mm Shaft Bore + Setscrew** (`socket`, *6-12mm shaft*) — the shaft bore
    and radial setscrew, defined by `bore_d`, `set_d`. Mates the shaft-spline
    commons members `spline-hub` and `knob-dshaft`.
- **Material awareness:** `tolerance_by_material` is declared — the bore should grow
  slightly for stiff filaments so the printed collar still slides onto the real
  shaft before the setscrew is tightened.
- **License:** CERN-OHL-W-2.0.

---

## Español

Un **collar de eje** se aprieta sobre un eje de transmisión redondo para fijar un
tope axial, espaciar un rodamiento o bloquear un cubo, generado con **CadQuery**
(B-Rep). Dimensionado al rango común de **6-12 mm** que comparte la familia
`shaft-spline`.

### Modos

| Modo | Pieza | Descripción |
| :--- | :--- | :--- |
| **Collar de Prisionero** | `setscrew_collar` | Anillo macizo con un barreno radial de prisionero que fija el collar al eje. |
| **Collar de Apriete (Partido)** | `clamp_collar` | Anillo con una ranura pasante en una pared y un perno transversal; al apretar cierra alrededor del eje sin marcarlo. |
| **Tope de Eje con Brida** | `shaft_stop` | Collar de prisionero con una brida base coaxial amplia como cara de asiento para un rodamiento o panel. |

### Por qué estas dimensiones

Los ejes de transmisión pequeños se agrupan en el rango de **6-12 mm** — el mismo
rango de barreno al que se acopla el resto de la familia shaft-spline. Un prisionero
radial **M4 (~4.3 mm)** es la fijación estándar para este tamaño; el collar partido
reutiliza ese mismo perno cruzando la separación. Un anillo rígido imprimible
requiere unos **5 mm** de pared para que el prisionero tenga material donde morder.

### Estanqueidad

Cada collar parte de un **cilindro macizo** con el barreno del eje cortado
**pasante**, ventilando por ambas caras. El chaflán del borde superior se aplica al
**anillo limpio ANTES** de cortar rasgos. Los orificios de prisionero y perno son
**pasantes**. La ranura del collar partido atraviesa una pared abriendo barreno→OD
como **separación real**. El tope con brida **une** un disco coaxial al material
compartido, dando un solo cuerpo. Validado estanco con `body_count == 1` en todos
los modos más los extremos mínimo y máximo.

- **Dominio:** industrial
- **Licencia:** CERN-OHL-W-2.0.
