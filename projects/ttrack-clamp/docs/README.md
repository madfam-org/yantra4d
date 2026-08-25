# T-Track Hold-Down Clamp

A parametric hold-down family generated with **CadQuery** (B-Rep) for standard
3/4 in woodworking T-track. A T-bolt rides in the track's lower channel and a
star knob tightens the clamp onto the workpiece. The interface is the real 3/4 in
(19.05 mm) slot and a sliding stud slot so the clamp reaches to fit.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## T-track reference

| Feature | Dimension |
| :--- | :--- |
| Slot mouth | 3/4 in = 19.05 mm |
| Channel depth | ≈ 3/8 in = 9.53 mm |
| Stud | 1/4-20 (≈ 6.6 mm clearance) |

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Pressing Arm** | `hold_down` | Low arm with a fore/aft stud slot; the nose overhangs the work. |
| **Step Block** | `step_block` | Staircase riser pressing several thicknesses; stud slot up the spine. |
| **Push / Stop Block** | `push_block` | L-shaped side stop registering an edge; one fixed stud hole. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Track & Stud | `stud` | 1/4-20 | Stud thread → clearance hole size. |
| Clamp Body | `body_len` | 70 mm | Length along the track. |
| Clamp Body | `body_w` | 22 mm | Width across the track. |
| Clamp Body | `body_h` | 14 mm | Base body height. |
| Clamp Body | `reach` | 18 mm | Nose / fence overhang. |
| Track & Stud | `slot_len` | 28 mm | Fore/aft stud-slot travel. |
| Clamp Body | `steps` | 4 | Step-block ledge count. |
| Track & Stud | `counterbore` | on | Recess the knob washer flush. |

## Presets

- **Standard Hold-Down** — the everyday 1/4-20 pressing arm.
- **Tall Step Block** — a five-ledge riser for varied stock thicknesses.
- **Edge Push / Stop** — a 5/16-18 side stop for registering a workpiece edge.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **3/4 in T-Track Stud Rail** (`rail`, 3/4in T-track — 19.05 mm slot,
    1/4-20 stud) — defined by `stud`, `body_w`, `slot_len`. Rides the same track
    as `bench-dog` and `featherboard`.
- **Material awareness:** `tolerance_by_material` tunes the stud clearance per
  filament so the T-bolt slides without slop.
- **Commons license:** CERN-OHL-W-2.0

---

# Prensa de Sujeción para Riel en T

Una familia de sujeciones paramétricas generada con **CadQuery** (B-Rep) para
riel en T de 3/4 in estándar en carpintería. Un tornillo en T corre por el canal
inferior del riel y una perilla de estrella aprieta la prensa sobre la pieza. La
interfaz es la ranura real de 3/4 in (19.05 mm) y una ranura deslizante para el
vástago que permite a la prensa alcanzar el ajuste.

Parte del **Commons de Hiperobjetos de Yantra4D**. Visualizador y configurador
oficial: [Yantra4D](https://app.yantra4d.com).

## Referencia de riel en T

| Característica | Dimensión |
| :--- | :--- |
| Boca de ranura | 3/4 in = 19.05 mm |
| Profundidad de canal | ≈ 3/8 in = 9.53 mm |
| Vástago | 1/4-20 (≈ 6.6 mm de holgura) |

## Modos

| Modo | Pieza | Descripción |
| :--- | :--- | :--- |
| **Brazo de Presión** | `hold_down` | Brazo bajo con ranura para el vástago; la nariz sobresale sobre la pieza. |
| **Bloque Escalonado** | `step_block` | Escalera que presiona varios espesores; ranura por la espina. |
| **Bloque de Tope** | `push_block` | Tope lateral en L que registra un borde; un orificio fijo. |

## Parámetros

| Grupo | Parámetro | Predeterminado | Notas |
| :--- | :--- | :--- | :--- |
| Riel y Vástago | `stud` | 1/4-20 | Rosca del vástago → tamaño del orificio. |
| Cuerpo de Prensa | `body_len` | 70 mm | Longitud a lo largo del riel. |
| Cuerpo de Prensa | `body_w` | 22 mm | Ancho a lo ancho del riel. |
| Cuerpo de Prensa | `body_h` | 14 mm | Altura base del cuerpo. |
| Cuerpo de Prensa | `reach` | 18 mm | Sobresaliente de nariz / valla. |
| Riel y Vástago | `slot_len` | 28 mm | Recorrido de la ranura del vástago. |
| Cuerpo de Prensa | `steps` | 4 | Número de escalones. |
| Riel y Vástago | `counterbore` | activado | Hundir la arandela de la perilla a ras. |

## Presets

- **Sujeción Estándar** — el brazo de presión 1/4-20 de uso diario.
- **Bloque Escalonado Alto** — un escalón de cinco niveles para espesores
  variados.
- **Tope de Borde** — un tope lateral 5/16-18 para registrar un borde.

## Perfil de Hiperobjeto

- **Dominio:** industrial
- **Interfaces CDG:**
  - **Riel de Vástago T-Track 3/4 in** (`rail`, riel en T de 3/4in — ranura de
    19.05 mm, vástago 1/4-20) — definido por `stud`, `body_w`, `slot_len`. Corre
    por el mismo riel que `bench-dog` y `featherboard`.
- **Conciencia de material:** `tolerance_by_material` ajusta la holgura del
  vástago por filamento para que el tornillo en T deslice sin juego.
- **Licencia commons:** CERN-OHL-W-2.0
