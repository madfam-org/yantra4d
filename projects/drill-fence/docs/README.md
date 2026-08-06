# Drill Press Fence

A parametric drill-press fence generated with **CadQuery** (B-Rep), with a flip
stop for repeatable hole spacing. The fence clamps to the table's **3/4 in
T-track** and carries a top channel a flip stop slides along — flip it up to
slide the workpiece past, flip it down to register the next position.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## T-track reference

| Feature | Dimension |
| :--- | :--- |
| Slot mouth | 3/4 in = 19.05 mm |
| Stud | 1/4-20 (≈ 6.6 mm clearance) |

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Fence Body** | `fence_body` | Tall bar with a top stop-channel and two table-mount slots. |
| **Flip Stop** | `flip_stop` | L stop that pivots on a pin and locks to the fence channel. |
| **Mount Bracket** | `mount_bracket` | Foot bracket clamping the fence to the table T-track. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Track & Stud | `stud` | 1/4-20 | Table stud thread → clearance hole. |
| Fence | `fence_len` | 180 mm | Fence face length. |
| Fence | `fence_h` | 45 mm | Fence face height. |
| Fence | `fence_t` | 12 mm | Fence bar thickness. |
| Fence | `channel_w` | 10 mm | Top stop-channel width. |
| Track & Stud | `mount_slot` | 40 mm | Table mount slot travel. |
| Fence | `stop_h` | 30 mm | Flip-stop register-face height. |

## Presets

- **Standard Drill Fence** — the everyday 1/4-20 fence body.
- **Tall Flip Stop** — a taller flip stop for thicker stock.
- **T-Track Mount** — the foot bracket for a 5/16-18 table.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **3/4 in T-Track Mount Rail** (`rail`, 3/4in T-track — 19.05 mm slot,
    1/4-20 stud) — `stud`, `mount_slot`. Clamps to the same track as `bench-dog`
    and `featherboard`.
  - **Flip-Stop Channel Rail** (`rail`, internal) — `channel_w`, `fence_len`.
- **Material awareness:** `tolerance_by_material` tunes the stud + channel
  clearance so the stop slides without slop.
- **Commons license:** CERN-OHL-W-2.0

---

# Guía para Taladro de Columna

Una guía para taladro de columna paramétrica generada con **CadQuery** (B-Rep),
con un tope abatible para espaciado repetible de agujeros. La guía se sujeta al
**riel en T de 3/4 in** de la mesa y lleva un canal superior por el que desliza
un tope — abátelo para pasar la pieza, bájalo para registrar la siguiente
posición.

Parte del **Commons de Hiperobjetos de Yantra4D**. Visualizador y configurador
oficial: [Yantra4D](https://app.yantra4d.com).

## Referencia de riel en T

| Característica | Dimensión |
| :--- | :--- |
| Boca de ranura | 3/4 in = 19.05 mm |
| Vástago | 1/4-20 (≈ 6.6 mm de holgura) |

## Modos

| Modo | Pieza | Descripción |
| :--- | :--- | :--- |
| **Cuerpo de Guía** | `fence_body` | Barra alta con canal de tope superior y dos ranuras de montaje. |
| **Tope Abatible** | `flip_stop` | Tope en L que pivota sobre un pasador y se fija al canal. |
| **Soporte de Montaje** | `mount_bracket` | Soporte de pie que sujeta la guía al riel en T de la mesa. |

## Parámetros

| Grupo | Parámetro | Predeterminado | Notas |
| :--- | :--- | :--- | :--- |
| Riel y Vástago | `stud` | 1/4-20 | Rosca del vástago de mesa → orificio. |
| Guía | `fence_len` | 180 mm | Longitud de la cara de la guía. |
| Guía | `fence_h` | 45 mm | Altura de la cara de la guía. |
| Guía | `fence_t` | 12 mm | Grosor de la barra de la guía. |
| Guía | `channel_w` | 10 mm | Ancho del canal de tope superior. |
| Riel y Vástago | `mount_slot` | 40 mm | Recorrido de las ranuras de montaje. |
| Guía | `stop_h` | 30 mm | Altura de la cara de registro del tope. |

## Presets

- **Guía de Taladro Estándar** — el cuerpo de guía 1/4-20 de uso diario.
- **Tope Abatible Alto** — un tope más alto para material grueso.
- **Montaje a Riel en T** — el soporte de pie para una mesa 5/16-18.

## Perfil de Hiperobjeto

- **Dominio:** industrial
- **Interfaces CDG:**
  - **Riel de Montaje T-Track 3/4 in** (`rail`, riel en T de 3/4in — ranura de
    19.05 mm, vástago 1/4-20) — `stud`, `mount_slot`. Se sujeta al mismo riel que
    `bench-dog` y `featherboard`.
  - **Riel de Canal del Tope** (`rail`, internal) — `channel_w`, `fence_len`.
- **Conciencia de material:** `tolerance_by_material` ajusta la holgura del
  vástago + canal para que el tope deslice sin juego.
- **Licencia commons:** CERN-OHL-W-2.0
