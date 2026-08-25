# Lead Screw Anti-Backlash Nut (T8)

A printable anti-backlash nut generated with **CadQuery** (B-Rep) for **T8** lead
screws — the repair/upgrade part for 3D-printer Z axes, small CNC stages and
linear actuators. A compression spring preloads the thread flanks so the nut
tracks the screw in both directions with **no lost motion**. The interface is a
genuine internal trapezoidal thread at the T8 nominal 8 mm major diameter and
2 mm pitch.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## T8 lead-screw reference

| Feature | Dimension |
| :--- | :--- |
| Major diameter | 8.0 mm |
| Pitch | 2.0 mm |
| Lead | 8 mm (4-start) |
| Thread form | trapezoidal, 30° included (15° flank) |

The nut is modelled single-start at the true 2 mm pitch: the major diameter and
pitch are dimensionally correct and it prints far more reliably than a 4-start
internal thread while still meshing the screw.

## Thread strategy

The bore is drilled to the thread **root** radius, then a trapezoidal rib is
swept along a genuine `cq.Wire.makeHelix` and **unioned** into the bore as
*positive material* (the bottle-thread idiom) — cutting a swept groove is far
slower and cracks the mesh. The rib is trimmed flush to its thread band so no
helical end spills past a face. The turn count is forced to a **half-integer**
(…3.5, 4.5…): an integer turn count degenerates the OCCT helical sweep into a
negative-volume body, so half-integers are both correct and fast.

On the spring nut the thread runs only **below** the spring pocket — the pocket
zone is the smooth annulus the spring rides in.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Spring Anti-Backlash Nut** | `spring_nut` | Threaded barrel + coaxial spring pocket + anti-rotation flats; the backlash-eliminating part. |
| **Solid Nut** | `solid_nut` | Plain single-piece T8 nut with wrench flats (tight reference). |
| **Flanged Nut** | `flanged_nut` | T8 nut on a bolt-down flange to fix it to a carriage. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Lead Screw | `screw` | T8 | Trapezoidal screw → major dia + pitch. |
| Nut Body | `body_dia` | 16 mm | Nut barrel outer diameter. |
| Nut Body | `height` | 18 mm | Height along the screw. |
| Lead Screw | `clearance` | 0.35 mm | Printed thread slop per side. |
| Spring & Flange | `spring_od` | 12 mm | Compression-spring outer diameter. |
| Spring & Flange | `spring_len` | 8 mm | Spring pocket depth. |
| Spring & Flange | `flange_dia` | 28 mm | Mounting-flange diameter. |
| Spring & Flange | `bolt_dia` | 3.4 mm | Flange bolt hole (M3). |
| Spring & Flange | `hole_count` | 4 | Flange bolt-hole count. |

## Presets

- **T8 Spring Anti-Backlash** — the classic spring-preloaded nut.
- **T8 Solid Nut** — a plain tight nut for setups that don't need take-up.
- **T8 Flanged Nut** — a bolt-down flanged nut.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **T8 Trapezoidal Thread** (`thread`, T8 leadscrew — 8 mm major, 2 mm pitch,
    8 mm lead) — the functional interface, defined by `screw`, `height`,
    `clearance`. A new cluster (no existing family member shares the T8 screw
    standard yet).
  - **Spring Preload Seat** (`pocket`, internal) — `spring_od`, `spring_len`.
- **Material awareness:** `tolerance_by_material` plus `clearance` let any
  printer make a nut that fits its own screw.
- **Commons license:** CERN-OHL-W-2.0

---

# Tuerca Anti-Holgura para Husillo (T8)

Una tuerca anti-holgura imprimible generada con **CadQuery** (B-Rep) para
husillos **T8** — la pieza de reparación y mejora para ejes Z de impresora 3D,
etapas CNC pequeñas y actuadores lineales. Un resorte de compresión precarga los
flancos de la rosca para que la tuerca siga al husillo en ambos sentidos **sin
juego**. La interfaz es una rosca trapezoidal interna real al diámetro mayor
nominal de 8 mm del T8 y paso de 2 mm.

Parte del **Commons de Hiperobjetos de Yantra4D**. Visualizador y configurador
oficial: [Yantra4D](https://app.yantra4d.com).

## Referencia de husillo T8

| Característica | Dimensión |
| :--- | :--- |
| Diámetro mayor | 8.0 mm |
| Paso | 2.0 mm |
| Avance | 8 mm (4 entradas) |
| Forma de rosca | trapezoidal, 30° incluido (flanco 15°) |

La tuerca se modela de una entrada al paso real de 2 mm: el diámetro mayor y el
paso son dimensionalmente correctos y se imprime mucho más fiable que una rosca
interna de 4 entradas, engranando igualmente el husillo.

## Estrategia de rosca

El barreno se perfora al radio de **raíz** de la rosca, luego se barre una
costilla trapezoidal por una hélice `cq.Wire.makeHelix` real y se **une** al
barreno como *material positivo* (el idioma de bottle-thread) — cortar una ranura
barrida es mucho más lento y agrieta la malla. La costilla se recorta a ras de su
banda de rosca para que ningún extremo helicoidal sobresalga de una cara. El
número de vueltas se fuerza a un **semi-entero** (…3.5, 4.5…): un número entero
de vueltas degenera el barrido helicoidal de OCCT en un cuerpo de volumen
negativo, así los semi-enteros son correctos y rápidos.

En la tuerca con resorte la rosca corre solo **debajo** del alojamiento del
resorte — la zona del alojamiento es el anillo liso por el que corre el resorte.

## Modos

| Modo | Pieza | Descripción |
| :--- | :--- | :--- |
| **Tuerca Anti-Holgura con Resorte** | `spring_nut` | Barril roscado + alojamiento coaxial + planos anti-giro; la pieza que elimina la holgura. |
| **Tuerca Sólida** | `solid_nut` | Tuerca T8 de una pieza con planos de llave (referencia ajustada). |
| **Tuerca con Brida** | `flanged_nut` | Tuerca T8 sobre brida atornillable para fijarla a un carro. |

## Parámetros

| Grupo | Parámetro | Predeterminado | Notas |
| :--- | :--- | :--- | :--- |
| Husillo | `screw` | T8 | Husillo trapezoidal → diámetro mayor + paso. |
| Cuerpo de Tuerca | `body_dia` | 16 mm | Diámetro exterior del barril. |
| Cuerpo de Tuerca | `height` | 18 mm | Altura a lo largo del husillo. |
| Husillo | `clearance` | 0.35 mm | Holgura de rosca impresa por lado. |
| Resorte y Brida | `spring_od` | 12 mm | Diámetro exterior del resorte. |
| Resorte y Brida | `spring_len` | 8 mm | Profundidad del alojamiento. |
| Resorte y Brida | `flange_dia` | 28 mm | Diámetro de la brida de montaje. |
| Resorte y Brida | `bolt_dia` | 3.4 mm | Orificio de perno de brida (M3). |
| Resorte y Brida | `hole_count` | 4 | Número de orificios de la brida. |

## Presets

- **Anti-Holgura T8 con Resorte** — la tuerca clásica precargada por resorte.
- **Tuerca Sólida T8** — una tuerca ajustada simple para montajes sin take-up.
- **Tuerca T8 con Brida** — una tuerca con brida atornillable.

## Perfil de Hiperobjeto

- **Dominio:** industrial
- **Interfaces CDG:**
  - **Rosca Trapezoidal T8** (`thread`, husillo T8 — 8 mm mayor, paso 2 mm,
    avance 8 mm) — la interfaz funcional, definida por `screw`, `height`,
    `clearance`. Un clúster nuevo (ningún miembro de familia existente comparte
    aún el estándar de husillo T8).
  - **Asiento de Precarga de Resorte** (`pocket`, internal) — `spring_od`,
    `spring_len`.
- **Conciencia de material:** `tolerance_by_material` y `clearance` permiten a
  cualquier impresora hacer una tuerca que encaje en su propio husillo.
- **Licencia commons:** CERN-OHL-W-2.0
