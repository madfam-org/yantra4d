# E26/E27 Socket Extender · Extensor de Portalámparas E26/E27

> Part of the **Yantra4D Hyperobjects Commons** · `e26-e27-lamp` family

## English

The **Lamp Socket Extender** extends and adapts Edison medium-screw lamp sockets
around the real E26/E27 standard. It is a mechanical adapter — a genuine
single-start helical Edison thread mates the same medium base that the
[`lampshade`](../../lampshade) and [`socket-adapter`](../../socket-adapter)
cartridges share, thickening the `e26-e27-lamp` family.

> **Not electrical-grade.** Printed lamp parts carry **no current**. This is a
> mechanical fit-and-mount adapter. Use certified lamp-holders, wire and
> insulation for any live connection, and follow local electrical code.

### Modes

| Mode | What it makes |
|------|---------------|
| **Socket Extender** | A female Edison socket that screws onto a lamp socket, a drop tube, and a male Edison shell on top that accepts the bulb — so a bulb sits `drop` mm lower / further out (e.g. into a shallow shade). |
| **E26/E27 Base Adapter** | A female Edison thread (base A) below and a male Edison thread (base B) above with a wiring channel through the middle — an **E26 ↔ E27 translator**. |
| **Device Shell** | A hollow male Edison shell with a top collar, to screw a printed device, sensor or holder into a lamp socket. |

### Key parameters

- **Lower / Socket Base** & **Upper / Bulb Base** — `E26` (26.05 mm) or `E27`
  (26.40 mm). Set them differently for a base translator.
- **Engagement Turns** — thread turns (snapped to a half-integer internally; real
  bases engage ~1.5–3 turns).
- **Thread Fit Clearance** — per-side slop between the printed thread and the
  metal base (0.4 mm suits most FDM printers).
- **Wall Thickness**, **Drop Length**, **Wiring Bore**, **Device Collar Height**.

### Hyperobject Profile

- **Domain:** household
- **CDG interface:** `edison_screw_base` — `thread`, standard **IEC 60061 E26 / E27 (7 TPI)**
- **Compatible with:** `lampshade`, `socket-adapter`
- **License:** CERN-OHL-W-2.0

The functional interface is a real 7-TPI (3.629 mm pitch) single-start Edison
thread. Threads are modeled as volumetric fused helical ribs (`makeHelix` +
swept trapezoid + boolean union), never boolean-cut grooves, and every socket
has a closed base disk so the mesh is watertight.

---

## Español

El **Extensor de Portalámparas E26/E27** extiende y adapta portalámparas Edison
de rosca media sobre el estándar real E26/E27. Es un adaptador mecánico — una
rosca Edison helicoidal de un solo inicio acopla la misma base media que
comparten los cartuchos [`lampshade`](../../lampshade) y
[`socket-adapter`](../../socket-adapter), engrosando la familia `e26-e27-lamp`.

> **No apto para uso eléctrico.** Las piezas de lámpara impresas **no conducen
> corriente**. Esto es un adaptador mecánico de ajuste y montaje. Usa
> portalámparas, cable y aislamiento certificados para cualquier conexión viva y
> sigue la normativa eléctrica local.

### Modos

| Modo | Qué genera |
|------|-----------|
| **Extensor de Portalámparas** | Un portalámparas Edison hembra que se atornilla a un portalámparas, un tubo de caída y una carcasa Edison macho arriba que acepta la bombilla — la bombilla queda `drop` mm más abajo / afuera. |
| **Adaptador de Base E26/E27** | Rosca Edison hembra (base A) abajo y rosca Edison macho (base B) arriba con un canal de cableado en medio — un **traductor E26 ↔ E27**. |
| **Carcasa de Dispositivo** | Una carcasa Edison macho hueca con collar superior, para atornillar un dispositivo, sensor o soporte impreso a un portalámparas. |

### Parámetros clave

- **Base Inferior / Portalámparas** y **Base Superior / Bombilla** — `E26`
  (26.05 mm) o `E27` (26.40 mm). Distintas entre sí para un traductor de base.
- **Vueltas de Rosca** — vueltas de rosca (se ajustan a un semi-entero
  internamente; las bases reales enroscan ~1.5–3 vueltas).
- **Holgura de Rosca** — holgura por lado entre la rosca impresa y la base
  metálica (0.4 mm sirve para la mayoría de impresoras FDM).
- **Grosor de Pared**, **Longitud de Caída**, **Orificio de Cableado**, **Altura
  del Collar de Dispositivo**.

### Perfil de Hiperobjeto

- **Dominio:** hogar (household)
- **Interfaz CDG:** `edison_screw_base` — `thread`, estándar **IEC 60061 E26 / E27 (7 TPI)**
- **Compatible con:** `lampshade`, `socket-adapter`
- **Licencia:** CERN-OHL-W-2.0

La interfaz funcional es una rosca Edison real de 7 TPI (paso de 3.629 mm) de un
solo inicio. Las roscas se modelan como nervaduras helicoidales volumétricas
fusionadas (`makeHelix` + trapecio barrido + unión booleana), nunca como surcos
cortados, y cada portalámparas tiene un disco de base cerrado para que la malla
sea hermética.
