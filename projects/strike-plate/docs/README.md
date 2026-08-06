# Door Strike Plate / Cerradero de Puerta

The **door strike plate** — the flat jamb-mortised plate a latch bolt or deadbolt
seats into — generated with **CadQuery** (B-Rep). Build a full-lip spring-latch
strike, the classic round-corner **1 in (25.4 mm)** deadbolt strike, or a
high-security box strike / reinforcer with four long screws into the stud.
Dimensions follow **ANSI/BHMA A156.2** residential strike hardware.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

---

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Full-Lip Latch Strike** | `latch_strike` | A spring-latch strike: a curved latch mouth open to the jamb edge, a radiused return lip the bolt ramps over, and two countersunk screws on the vertical centreline. |
| **Round-Corner Deadbolt Strike** | `deadbolt_strike` | The classic deadbolt strike: a **1 in (25.4 mm)** bolt bore through a 1-1/8 × 2-1/4 in round-corner plate with two countersunk screws. |
| **High-Security Box Strike** | `box_strike` | A box strike / reinforcer: a thicker plate with a recessed bolt pocket open to the jamb and **four long screw bores** that reach past the jamb into the wall stud. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Plate Body | `plate_w` | 28.58 mm | Plate width (ANSI 1-1/8 in). |
| Plate Body | `plate_h` | 57.15 mm | Plate height (ANSI 2-1/4 in); screw spacing derives from this. |
| Plate Body | `plate_t` | 3.0 mm | Plate thickness (box strike adds 2 mm). |
| Plate Body | `corner_r` | 3.2 mm | Rounded corner radius (~1/8 in). |
| Bolt / Latch Bore | `bolt_bore_d` | 25.40 mm | Deadbolt bore (1 in standard). |
| Bolt / Latch Bore | `latch_bore_w` | 16.0 mm | Spring-latch mouth width. |
| Mounting Screws | `screw_d` / `screw_head_d` | 4.2 / 8.4 mm | #8/#10 shank and countersink head. |
| Mounting Screws | `box_screw_d` | 4.8 mm | Long box-strike anchor screw. |

## Why these dimensions

Residential strike hardware under **ANSI/BHMA A156.2** centres on a **1-1/8 in ×
2-1/4 in (28.58 × 57.15 mm)** plate with rounded corners and #8/#10 wood screws.
The deadbolt strike bore is **1 in (25.40 mm)**. The two mounting screws sit on the
vertical centreline, spaced from the plate length so they always land inside the
plate. The box strike thickens the plate and moves to four corner screws — the real
security upgrade is **long screws that bite the wall stud**, not just the jamb.

## Watertightness

Every strike is a **filleted rectangular blank**; fillets are applied to the clean
blank **before** any feature is cut (filleting a feature-laden solid crashes the
OCCT cleaner). Screw bores are through-holes with countersinks that vent to the top
face; the latch mouth and box pocket open to the jamb edge — every cut vents to a
face, so no sealed cavity forms. The curved latch lip is a **boolean of overlapping
solids** (box minus cylinder), never a revolve of a cut profile, and is intersected
back to the plate footprint so it welds flush into shared material. Validated
watertight with `body_count == 1` across all modes plus an extreme thin-plate /
oversize-bore case.

## Presets

- **ANSI Deadbolt Strike (1 in bore)** — the reference deadbolt strike at spec.
- **Full-Lip Latch Strike** — the spring-latch plate with its return lip.
- **Heavy-Duty Box Reinforcer** — a taller, thicker four-screw jamb reinforcer.

## Hyperobject Profile

- **Domain:** infrastructure
- **CDG interfaces:**
  - **Deadbolt Bolt Bore** (`socket`, *ANSI/BHMA A156.2 deadbolt strike, 1 in
    bore*) — the bolt seat, defined by `bolt_bore_d`.
  - **Strike Screw Pattern** (`bolt_pattern`, *standard strike, #8/#10 wood screw*)
    — the two-screw centreline pattern, defined by `plate_h`, `screw_d`.
- **Material awareness:** `tolerance_by_material` is declared — the bolt bore and
  screw clearances should grow slightly for stiff filaments and shrink for
  flexibles so the printed strike still accepts the hardware.
- **License:** CERN-OHL-W-2.0.

---

## Español

La **placa de cerradero** — la placa plana embutida en el marco donde se aloja el
pestillo o el cerrojo — generada con **CadQuery** (B-Rep).

### Modos

| Modo | Pieza | Descripción |
| :--- | :--- | :--- |
| **Cerradero de Labio (Pestillo)** | `latch_strike` | Cerradero de pestillo de resorte: boca curva abierta al borde del marco, labio de retorno redondeado y dos tornillos avellanados en la línea central. |
| **Cerradero de Cerrojo Redondeado** | `deadbolt_strike` | El cerradero clásico: perforación de cerrojo de **1 in (25.4 mm)** en una placa de esquinas redondeadas de 1-1/8 × 2-1/4 in con dos tornillos avellanados. |
| **Cerradero de Caja (Alta Seguridad)** | `box_strike` | Cerradero de caja / refuerzo: placa más gruesa con bolsillo rebajado abierto al marco y **cuatro perforaciones para tornillos largos** que llegan al montante de la pared. |

### Por qué estas dimensiones

El hardware residencial según **ANSI/BHMA A156.2** se centra en una placa de
**1-1/8 × 2-1/4 in (28.58 × 57.15 mm)** con esquinas redondeadas y tornillos para
madera #8/#10. La perforación del cerrojo es de **1 in (25.40 mm)**. La mejora de
seguridad real del cerradero de caja son los **tornillos largos que agarran el
montante**, no solo el marco.

### Estanqueidad

Cada cerradero es una **placa rectangular con filetes** aplicados al bloque limpio
**antes** de cortar cualquier detalle. Todas las perforaciones ventilan a una cara,
por lo que no se forma ninguna cavidad sellada. El labio curvo es un **booleano de
sólidos superpuestos**, nunca una revolución de un perfil cortado. Validado estanco
con `body_count == 1` en todos los modos más un caso extremo.

- **Dominio:** infrastructure
- **Licencia:** CERN-OHL-W-2.0.
