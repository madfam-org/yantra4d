# T-Slot Corner Bracket

A parametric corner joiner generated with **CadQuery** (B-Rep) for aluminium
T-slot extrusion (2020 / 2040 / OpenBuilds). The bracket bolts into the
extrusion's T-slots with M5 drop-in nuts on the real 20 mm module grid, with one
fastener centred on each slot's centre-line.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Extrusion table

| Series | Module | Slot | Fastener |
| :--- | :--- | :--- | :--- |
| 2020 | 20 mm | 6 mm | M5 |
| 2040 | 20 mm | 6 mm | M5 |
| 3030 | 30 mm | 8 mm | M6 |
| 4040 | 40 mm | 8 mm | M8 |

The bolt centre lands at `module / 2` from the extrusion corner, i.e. on the
slot centre-line, so a printed bracket registers exactly like a die-cast one.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Two-Way Brace** | `corner_2way` | Flat right-angle plate, one counter-bored M-hole per leg. |
| **Gusseted Brace** | `corner_gusset` | Two-way plate plus a triangular web across the inner angle. |
| **Three-Way Block** | `corner_3way` | Cubic vertex block joining three extrusions (X, Y, Z arms). |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Extrusion | `series` | 2020 | Module + fastener size from the table. |
| Bracket | `thickness` | 6.0 mm | Leg / arm thickness. |
| Bracket | `leg_len` | 30.0 mm | Length of each leg along the extrusion. |
| Bracket | `width` | 20.0 mm | Width across the extrusion face. |
| Bracket | `bolt_dia` | 0.0 mm | Override clearance; 0 = derive from series. |
| Bracket | `fillet_r` | 3.0 mm | Outer-corner radius. |

## Presets

- **2020 Two-Way Brace** — the workhorse inside-corner brace for a 2020 frame.
- **2040 Gusseted Brace** — a reinforced brace for load-bearing 2040 members.
- **3030 Three-Way Vertex** — a cubic block joining three 3030 extrusions.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **T-Slot M5 Bolt Grid** (`profile`, 2020/2040 extrusion — 20 mm module,
    6 mm slot, M5) — the interface, defined by `series`, `leg_len`, `width`,
    `bolt_dia`. Shares the T-slot extrusion standard with `tslot-2020`,
    `featherboard`, and `linear-wheel`.
- **Material awareness:** `tolerance_by_material` lets the M-clearance be tuned
  per filament so drop-in nuts thread cleanly.
- **Commons license:** CERN-OHL-W-2.0

---

# Soporte de Esquina T-Slot

Una unión de esquina paramétrica generada con **CadQuery** (B-Rep) para perfil
de aluminio T-slot (2020 / 2040 / OpenBuilds). El soporte se atornilla a las
ranuras T del perfil con tuercas M5 sobre la cuadrícula real de módulo de 20 mm,
con un tornillo centrado en la línea central de cada ranura.

Parte del **Commons de Hiperobjetos de Yantra4D**. Visualizador y configurador
oficial: [Yantra4D](https://app.yantra4d.com).

## Tabla de perfiles

| Serie | Módulo | Ranura | Tornillo |
| :--- | :--- | :--- | :--- |
| 2020 | 20 mm | 6 mm | M5 |
| 2040 | 20 mm | 6 mm | M5 |
| 3030 | 30 mm | 8 mm | M6 |
| 4040 | 40 mm | 8 mm | M8 |

El centro del tornillo cae a `módulo / 2` de la esquina del perfil, es decir
sobre la línea central de la ranura, así una escuadra impresa registra igual que
una de fundición.

## Modos

| Modo | Pieza | Descripción |
| :--- | :--- | :--- |
| **Escuadra de Dos Vías** | `corner_2way` | Placa plana en ángulo recto, un orificio M avellanado por pata. |
| **Escuadra con Refuerzo** | `corner_gusset` | Placa de dos vías más un alma triangular en el ángulo interior. |
| **Bloque de Tres Vías** | `corner_3way` | Bloque cúbico de vértice que une tres perfiles (brazos X, Y, Z). |

## Parámetros

| Grupo | Parámetro | Predeterminado | Notas |
| :--- | :--- | :--- | :--- |
| Perfil | `series` | 2020 | Módulo + tamaño de tornillo de la tabla. |
| Soporte | `thickness` | 6.0 mm | Grosor de pata / brazo. |
| Soporte | `leg_len` | 30.0 mm | Longitud de cada pata a lo largo del perfil. |
| Soporte | `width` | 20.0 mm | Ancho a lo ancho de la cara del perfil. |
| Soporte | `bolt_dia` | 0.0 mm | Sobrescribir holgura; 0 = derivar de la serie. |
| Soporte | `fillet_r` | 3.0 mm | Radio de esquina exterior. |

## Presets

- **Escuadra 2020 de Dos Vías** — la escuadra de esquina interior para un
  bastidor 2020.
- **Escuadra 2040 con Refuerzo** — una escuadra reforzada para miembros 2040 con
  carga.
- **Vértice 3030 de Tres Vías** — un bloque cúbico que une tres perfiles 3030.

## Perfil de Hiperobjeto

- **Dominio:** industrial
- **Interfaces CDG:**
  - **Cuadrícula de Pernos M5 T-Slot** (`profile`, perfil 2020/2040 — módulo de
    20 mm, ranura de 6 mm, M5) — la interfaz, definida por `series`, `leg_len`,
    `width`, `bolt_dia`. Comparte el estándar de extrusión T-slot con
    `tslot-2020`, `featherboard` y `linear-wheel`.
- **Conciencia de material:** `tolerance_by_material` permite ajustar la holgura
  M por filamento para que las tuercas entren limpiamente.
- **Licencia commons:** CERN-OHL-W-2.0
