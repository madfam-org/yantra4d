# Cam-Lock Latch Set / Juego de Cierre de Cerradura de Leva

The companion pieces a furniture / cabinet **cam lock** catches against,
generated with **CadQuery** (B-Rep). The `lock-cam` cartridge builds the swinging
cam; this set builds the frame-side parts it meets: a **strike plate** the cam
swings into, a stepped **body bushing** that adapts an oversize mounting hole back
down to the standard **16/19 mm** cam-lock body, and a **keeper block** with an
undercut ledge. Sized to the two dominant furniture cam-lock body diameters.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

---

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Strike Plate** | `strike_plate` | A flat plate with a receiving slot the cam swings into, flanked by two countersunk frame screws. |
| **Body Bushing (Adapter)** | `body_bushing` | A stepped sleeve that fills an oversize / worn mounting hole and bores back down to the 16/19 mm body, with a top flange that stops at the surface. |
| **Keeper Block** | `keeper_block` | A raised catch block with an undercut ledge that gives the cam a positive shelf to hook behind, plus screw fixings. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Cam-Lock Body | `body_d` | 16.0 mm | Threaded body Ø (16/19 mm furniture standards). |
| Cam-Lock Body | `hole_d` | 22.0 mm | Oversize mounting hole the bushing fills (`body_bushing`; must exceed `body_d`). |
| Plate & Catch | `plate_t` | 4.0 mm | Strike / keeper base plate thickness. |
| Plate & Catch | `cam_clear` | 3.0 mm | Slot / ledge clearance for the ~2-2.5 mm cam plate. |
| Plate & Catch | `keep_h` | 8.0 mm | Keeper catch-block height / bushing barrel grip depth. |
| Fixing | `screw_d` | 3.6 mm | Frame fixing screw shank (#6 / M3.5 ~3.6 mm). |

## Why these dimensions

Furniture and cabinet cam locks use a threaded body of **16 mm** or **19 mm**
diameter — the same standard the `lock-cam` cartridge keys to, so the whole
cam-lock commons family shares one mounting bore. The cam plate is ~**2-2.5 mm**
steel reaching ~43 mm, so the strike slot and keeper ledge open a **cam_clear**
gap sized to let that plate swing in. Frame fixings are **#6 / M3.5 (~3.6 mm)**
wood screws with a ~7 mm head, countersunk flush into the plate.

## Watertightness

The strike and keeper start as **filleted flat blanks** — vertical corners
rounded on the CLEAN blank BEFORE any feature is cut. The receiving slot is an
obround cut fully **through** the plate (vents both faces); countersunk screw
holes are **through-bores** with the countersink built as a short **lofted**
widening cylinder from the top face (never a revolve of a cut profile). The body
bushing **unions** two coaxial cylinders (barrel + flange) and bores the body
straight **through** (open both ends). The keeper's catch ledge is a
**through-pocket** that opens to a side face, so it vents to outside — no sealed
cavity. Validated watertight with `body_count == 1` across all three modes plus
the minimum and maximum parameter extremes.

## Presets

- **16 mm Strike Plate** — the smaller furniture standard at spec.
- **19 mm Body Bushing** — an adapter for a worn 19 mm mount.
- **16 mm Keeper Block** — a positive catch for a sagging door.

## Hyperobject Profile

- **Domain:** infrastructure
- **CDG interfaces:**
  - **16/19 mm Cam-Lock Body** (`socket`, *16/19mm cam-lock*) — the body mounting
    bore and oversize-hole adapter, defined by `body_d`, `hole_d`. Mates the
    cam-lock commons member `lock-cam`.
- **Material awareness:** `tolerance_by_material` is declared — the body bore and
  slot should grow slightly for stiff filaments so the printed latch still fits
  the real cam-lock hardware.
- **License:** CERN-OHL-W-2.0.

---

## Español

Las piezas complementarias contra las que engancha una **cerradura de leva** de
mobiliario, generadas con **CadQuery** (B-Rep). El cartucho `lock-cam` construye la
leva giratoria; este juego construye las piezas del lado del marco: una **placa de
cierre**, un **buje de cuerpo** escalonado que adapta un agujero sobredimensionado
al cuerpo estándar de **16/19 mm**, y un **bloque retén** con reborde socavado.

### Modos

| Modo | Pieza | Descripción |
| :--- | :--- | :--- |
| **Placa de Cierre** | `strike_plate` | Placa plana con ranura receptora donde gira la leva, con dos tornillos avellanados. |
| **Buje de Cuerpo (Adaptador)** | `body_bushing` | Casquillo escalonado que llena un agujero sobredimensionado y barrena al cuerpo de 16/19 mm, con brida superior. |
| **Bloque Retén** | `keeper_block` | Bloque de enganche elevado con reborde socavado que da a la leva un tope positivo, más tornillos. |

### Por qué estas dimensiones

Las cerraduras de leva de mobiliario usan un cuerpo roscado de **16 mm** o **19 mm**
— el mismo estándar al que se acopla `lock-cam`. La placa de leva es de ~**2-2.5 mm**
de acero, así que la ranura del cierre y el reborde del retén abren una holgura
**cam_clear** para que entre esa placa. Las fijaciones son tornillos **#6 / M3.5
(~3.6 mm)** avellanados a ras de la placa.

### Estanqueidad

El cierre y el retén parten de **bloques planos fileteados** — esquinas redondeadas
en el bloque limpio ANTES de cortar rasgos. La ranura receptora atraviesa la placa
(ventila por ambas caras); los avellanados son **pasantes** con el avellanado hecho
como cilindro **lofteado** desde la cara superior. El buje **une** dos cilindros
coaxiales y barrena el cuerpo **pasante**. El reborde del retén es un **hueco
pasante** que abre a una cara lateral, ventilando al exterior. Validado estanco con
`body_count == 1` en todos los modos más los extremos mínimo y máximo.

- **Dominio:** infrastructure
- **Licencia:** CERN-OHL-W-2.0.
