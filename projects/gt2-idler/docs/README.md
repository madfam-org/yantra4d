# GT2 Belt Idler Bracket

A parametric idler + tensioner family generated with **CadQuery** (B-Rep) for
**GT2 2 mm** synchronous belts — the belt on nearly every desktop 3D printer,
small CNC and plotter. The idler runs on a **608** bearing; the tensioner bracket
bolts to the frame through slotted holes to dial in belt tension. Two real
interfaces meet: the GT2 tooth profile and the 608 press-fit seat.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## GT2 reference

| Feature | Dimension |
| :--- | :--- |
| Pitch | 2.0 mm |
| Tooth depth | 0.76 mm |
| Pitch-line differential | 0.254 mm |
| Idler bearing | 608 (8×22×7) |

GT2 belts run on the smooth back of a toothless idler; a toothed idler meshes the
teeth. A GT2 valley is approximated by a circular arc on the pitch circle — a
close, watertight stand-in (the timing-pulley idiom). A GT2 idler carries a 608
only once its diameter is large enough; a small toothed idler takes a shaft bore.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Smooth Idler** | `smooth_idler` | Toothless flanged barrel; belt back runs on it; 608 seat. |
| **Toothed Idler** | `toothed_idler` | GT2-toothed idler that meshes the belt; bore scales with size. |
| **Tensioner Bracket** | `tensioner_bracket` | L bracket with an idler stud + slotted frame bolts. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Belt & Idler | `belt_type` | GT2-2mm | Synchronous belt profile. |
| Belt & Idler | `teeth` | 20 | Toothed-idler tooth count → pitch diameter. |
| Belt & Idler | `belt_width` | 7 mm | Belt running width. |
| Belt & Idler | `od` | 18 mm | Smooth-idler outside diameter. |
| Belt & Idler | `flange_h` | 2.0 mm | Retaining flange rim height. |
| Tensioner | `arm_len` | 40 mm | Bracket base-foot length. |
| Tensioner | `slot_len` | 12 mm | Tension-slot slide travel. |
| Tensioner | `bolt_dia` | 4.5 mm | Frame bolt clearance (M4). |

## Presets

- **GT2 Smooth 608 Idler** — the standard smooth back-running idler.
- **GT2 20T Toothed Idler** — a 20-tooth meshing idler.
- **GT2 Belt Tensioner** — the L bracket for setting belt tension.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **GT2 Tooth Profile** (`profile`, GT2 2mm belt) — `belt_type`, `teeth`,
    `belt_width`. Meshes the same GT2 profile as `belt-clamp` and
    `timing-pulley`.
  - **608 Idler Seat** (`socket`, 608 bearing ISO 15 — 8×22×7) — shares the
    22 mm seat with `bearing-housing` and `linear-wheel`.
  - **Frame Tension Bolt Pattern** (`bolt_pattern`, internal) — `arm_len`,
    `slot_len`, `bolt_dia`.
- **Material awareness:** `tolerance_by_material` tunes the seat + tooth
  clearance to the filament.
- **Commons license:** CERN-OHL-W-2.0

---

# Soporte Tensor de Correa GT2

Una familia de poleas + tensor paramétrica generada con **CadQuery** (B-Rep)
para correas síncronas **GT2 2 mm** — la correa de casi toda impresora 3D de
escritorio, CNC pequeño y plóter. La polea gira sobre un rodamiento **608**; el
soporte tensor se atornilla al bastidor por ranuras para ajustar la tensión. Se
encuentran dos interfaces reales: el perfil de diente GT2 y el asiento a presión
del 608.

Parte del **Commons de Hiperobjetos de Yantra4D**. Visualizador y configurador
oficial: [Yantra4D](https://app.yantra4d.com).

## Referencia GT2

| Característica | Dimensión |
| :--- | :--- |
| Paso | 2.0 mm |
| Profundidad de diente | 0.76 mm |
| Diferencial de línea primitiva | 0.254 mm |
| Rodamiento de polea | 608 (8×22×7) |

Las correas GT2 corren por el dorso liso de una polea sin dientes; una polea
dentada engrana los dientes. Un valle GT2 se aproxima con un arco circular sobre
el círculo primitivo — un sustituto cercano y estanco (el idioma de
timing-pulley). Una polea GT2 aloja un 608 solo cuando su diámetro es
suficiente; una polea dentada pequeña usa un barreno de eje.

## Modos

| Modo | Pieza | Descripción |
| :--- | :--- | :--- |
| **Polea Lisa** | `smooth_idler` | Barril liso con pestañas; el dorso de la correa corre sobre él; asiento 608. |
| **Polea Dentada** | `toothed_idler` | Polea GT2 dentada que engrana la correa; el barreno escala con el tamaño. |
| **Soporte Tensor** | `tensioner_bracket` | Soporte en L con vástago de polea + pernos ranurados al bastidor. |

## Parámetros

| Grupo | Parámetro | Predeterminado | Notas |
| :--- | :--- | :--- | :--- |
| Correa y Polea | `belt_type` | GT2-2mm | Perfil de correa síncrona. |
| Correa y Polea | `teeth` | 20 | Dientes de la polea → diámetro primitivo. |
| Correa y Polea | `belt_width` | 7 mm | Ancho de rodadura de la correa. |
| Correa y Polea | `od` | 18 mm | Diámetro exterior de la polea lisa. |
| Correa y Polea | `flange_h` | 2.0 mm | Altura del borde de la pestaña. |
| Tensor | `arm_len` | 40 mm | Longitud del pie base del soporte. |
| Tensor | `slot_len` | 12 mm | Recorrido de la ranura de tensión. |
| Tensor | `bolt_dia` | 4.5 mm | Holgura del perno del bastidor (M4). |

## Presets

- **Polea Lisa GT2 608** — la polea lisa estándar de rodadura por el dorso.
- **Polea Dentada GT2 20D** — una polea dentada de 20 dientes.
- **Tensor de Correa GT2** — el soporte en L para ajustar la tensión.

## Perfil de Hiperobjeto

- **Dominio:** industrial
- **Interfaces CDG:**
  - **Perfil de Diente GT2** (`profile`, correa GT2 2mm) — `belt_type`, `teeth`,
    `belt_width`. Engrana el mismo perfil GT2 que `belt-clamp` y `timing-pulley`.
  - **Asiento de Polea 608** (`socket`, rodamiento 608 ISO 15 — 8×22×7) —
    comparte el asiento de 22 mm con `bearing-housing` y `linear-wheel`.
  - **Patrón de Pernos de Tensión** (`bolt_pattern`, internal) — `arm_len`,
    `slot_len`, `bolt_dia`.
- **Conciencia de material:** `tolerance_by_material` ajusta la holgura del
  asiento + diente al filamento.
- **Licencia commons:** CERN-OHL-W-2.0
