# Cabinet Cam-Lock Cam / Leva de Cerradura de Gabinete

The flat steel **cam** that bolts to the back of a cabinet cam-lock cylinder and
swings to catch behind the frame, generated with **CadQuery** (B-Rep). Build a
straight cam for a **16 mm-body** lock, a straight cam for a **19 mm-body** lock,
or a **cranked offset cam** for deep-set doors. Sized to the two dominant furniture
cam-lock body diameters.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

---

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **16 mm Cam (Straight)** | `cam_16mm` | Straight cam for a **16 mm-body** cam lock — the smaller standard. A collar bores the body, a slotted socket keys the tailpiece, a screw fixes the cam. |
| **19 mm Cam (Straight)** | `cam_19mm` | Straight cam for a **19 mm-body** cam lock — the larger standard. The collar bore and outer diameter grow to the 19 mm body. |
| **Cranked Offset Cam** | `offset_cam` | A stepped cam whose catch face is raised in Z by a ramp, for deep-set doors where a flat cam would not reach the frame. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Lock Body | `body_d` | 16.0 mm | Threaded body Ø (16/19 mm standards). 19 mm mode enforces ≥ 19 mm. |
| Cam Plate | `cam_reach` | 43.0 mm | Arm length from lock axis to catch tip. |
| Cam Plate | `cam_w` | 14.0 mm | Cam arm width. |
| Cam Plate | `cam_t` | 2.5 mm | Plate thickness. |
| Cam Plate | `offset_z` | 8.0 mm | Catch Z-offset (`offset_cam` only). |
| Tailpiece Drive | `tail_w` / `tail_len` | 6.0 / 9.0 mm | Keyed tailpiece drive socket. |
| Tailpiece Drive | `screw_d` | 3.4 mm | Axial fixing-screw clearance (M3-ish). |

## Why these dimensions

Standard furniture and cabinet cam locks use a threaded body of **16 mm** or
**19 mm** diameter — the mounting hole must match the body for a snug fit. The cam
plate reaches roughly **43 mm** from the lock axis and is ~2 mm steel. The cam keys
onto a slotted / D-flat tailpiece (modelled here as a keyed slot socket) and is
pinned by an axial screw. The two straight cams differ by body diameter; the offset
cam cranks its catch face up in Z for doors set deeper than a flat cam can span.

## Watertightness

The cam arm is a **stadium (obround) blank** — already round-ended, so no edge
fillet is needed (and none that could crash the OCCT cleaner). The hub collar is a
cylinder **unioned** into the arm where they overlap, welding into one body. The
tailpiece socket is a keyed slot cut fully **through** the collar (opens top and
bottom), and the fixing screw is a **through-bore** — both vent to outside, so no
sealed cavity. The offset cam joins a low slab and a raised slab with a **lofted
ramp wedge**; every join overlaps into shared material, yielding a single manifold
body. Validated watertight with `body_count == 1` across all modes plus an extreme
oversize case.

## Presets

- **Standard 16 mm Cam** — the smaller furniture standard at spec.
- **Standard 19 mm Cam** — the larger furniture standard at spec.
- **Deep-Door Offset Cam** — a 19 mm cranked cam for a deep-set door.

## Hyperobject Profile

- **Domain:** infrastructure
- **CDG interfaces:**
  - **Cam-Lock Body Socket** (`socket`, *16/19mm cam lock (furniture)*) — the body
    mounting bore, defined by `body_d`.
  - **Tailpiece Drive Key** (`socket`, *slotted cam-lock tailpiece*) — the keyed
    drive socket, defined by `tail_w`, `tail_len`.
- **Material awareness:** `tolerance_by_material` and `recycled_material_toggle`
  are declared — the body bore and drive socket should grow slightly for stiff
  filaments so the printed cam still keys onto the real hardware.
- **License:** CERN-OHL-W-2.0.

---

## Español

La **leva** plana de acero que se atornilla detrás del cilindro de una cerradura de
leva de gabinete y gira para engancharse tras el marco, generada con **CadQuery**
(B-Rep). Dimensionada a los dos diámetros de cuerpo dominantes (16/19 mm).

### Modos

| Modo | Pieza | Descripción |
| :--- | :--- | :--- |
| **Leva 16 mm (Recta)** | `cam_16mm` | Leva recta para cerradura de cuerpo de **16 mm** — el estándar menor. |
| **Leva 19 mm (Recta)** | `cam_19mm` | Leva recta para cerradura de cuerpo de **19 mm** — el estándar mayor. |
| **Leva Acodada con Desfase** | `offset_cam` | Leva escalonada cuyo enganche se eleva en Z por una rampa, para puertas profundas. |

### Por qué estas dimensiones

Las cerraduras de leva de mobiliario usan un cuerpo roscado de **16 mm** o **19 mm**
de diámetro; el agujero de montaje debe coincidir con el cuerpo. La placa alcanza
unos **43 mm** desde el eje y es de ~2 mm de acero. La leva encaja en una espiga
ranurada / con plano D (modelada como alojamiento ranurado) y se fija con un
tornillo axial.

### Estanqueidad

El brazo es un **bloque en estadio (obround)**, ya redondeado en la punta. El collar
cilíndrico se **une** al brazo donde se superponen. El alojamiento de la espiga
atraviesa el collar (ventila arriba y abajo) y el tornillo es un **agujero
pasante** — sin cavidad sellada. La leva con desfase une dos losas con una **cuña
en rampa**; todo se superpone en material compartido, dando un solo cuerpo.
Validado estanco con `body_count == 1` en todos los modos más un caso extremo.

- **Dominio:** infrastructure
- **Licencia:** CERN-OHL-W-2.0.
