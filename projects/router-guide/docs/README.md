# Router Template Guide

A parametric template-routing family generated with **CadQuery** (B-Rep): guide
bushings and adapters on the universal Porter-Cable flange pattern. A guide
bushing drops into the router sub-base through the standard flange hole; its
barrel rides a template edge while the bit passes through the centre, so the cut
follows the template offset by the bushing wall.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Bushing reference (Porter-Cable universal)

| Feature | Dimension |
| :--- | :--- |
| Flange OD | 1-3/8 in = 34.93 mm |
| Flange seat | 1-3/16 in = 30.16 mm |
| Flange thickness | ≈ 0.150 in = 3.8 mm |
| Barrel ODs | 5/16, 3/8, 7/16, 1/2, 5/8, 3/4 in |

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Guide Bushing** | `guide_bushing` | Flange + projecting barrel with a bit-clearance bore; rides the template. |
| **Baseplate Adapter** | `baseplate_adapter` | Ring that seats the universal flange and bolts to any router sub-base. |
| **Offset Collar** | `offset_collar` | Split collar that enlarges a barrel's OD to set a precise template offset. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Bushing | `barrel` | 1/2 in | Barrel OD (inch designation). |
| Bushing | `barrel_len` | 8 mm | Barrel projection below the flange. |
| Bushing | `bit_clear` | 0.4 mm | Extra bit-bore clearance. |
| Bushing | `wall` | 2.0 mm | Barrel wall thickness. |
| Adapter & Collar | `plate_dia` | 90 mm | Adapter ring diameter. |
| Adapter & Collar | `bolt_circle` | 60 mm | Sub-base mount bolt circle. |
| Adapter & Collar | `bolt_dia` | 4.5 mm | Mount bolt clearance (M4). |
| Adapter & Collar | `hole_count` | 3 | Mount bolt count. |
| Adapter & Collar | `offset` | 3.0 mm | Radius the offset collar adds. |

## Presets

- **1/2 in Guide Bushing** — the everyday half-inch bushing.
- **Universal Baseplate Adapter** — fits the standard flange to any router.
- **3 mm Offset Collar** — a fixed 3 mm template-to-cut offset.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **Universal Router-Bushing Flange** (`socket`, router bushing — Porter-Cable
    universal 1-3/8 in flange) — the interface, defined by `barrel`,
    `barrel_len`, `wall`. A new cluster (no existing family member shares the
    router-bushing standard yet).
  - **Sub-Base Bolt Circle** (`bolt_pattern`, internal) — `bolt_circle`,
    `bolt_dia`, `hole_count`.
- **Material awareness:** `tolerance_by_material` plus `wall` and `bit_clear`
  dial a bushing to a specific bit and template offset.
- **Commons license:** CERN-OHL-W-2.0

---

# Guía de Plantilla para Fresadora

Una familia de fresado con plantilla paramétrica generada con **CadQuery**
(B-Rep): casquillos guía y adaptadores sobre el patrón de brida universal
Porter-Cable. Un casquillo guía se inserta en la base de la fresadora por el
orificio de brida estándar; su barril sigue el borde de la plantilla mientras la
broca pasa por el centro, así el corte sigue la plantilla desplazado por la pared
del casquillo.

Parte del **Commons de Hiperobjetos de Yantra4D**. Visualizador y configurador
oficial: [Yantra4D](https://app.yantra4d.com).

## Referencia de casquillo (Porter-Cable universal)

| Característica | Dimensión |
| :--- | :--- |
| DE de brida | 1-3/8 in = 34.93 mm |
| Asiento de brida | 1-3/16 in = 30.16 mm |
| Grosor de brida | ≈ 0.150 in = 3.8 mm |
| DE de barril | 5/16, 3/8, 7/16, 1/2, 5/8, 3/4 pulg |

## Modos

| Modo | Pieza | Descripción |
| :--- | :--- | :--- |
| **Casquillo Guía** | `guide_bushing` | Brida + barril con barreno de broca; sigue la plantilla. |
| **Adaptador de Base** | `baseplate_adapter` | Anillo que aloja la brida universal y se atornilla a cualquier base. |
| **Collar de Desplazamiento** | `offset_collar` | Collar partido que agranda el DE del barril para un desplazamiento preciso. |

## Parámetros

| Grupo | Parámetro | Predeterminado | Notas |
| :--- | :--- | :--- | :--- |
| Casquillo | `barrel` | 1/2 pulg | DE del barril (designación en pulgadas). |
| Casquillo | `barrel_len` | 8 mm | Proyección del barril bajo la brida. |
| Casquillo | `bit_clear` | 0.4 mm | Holgura adicional del barreno. |
| Casquillo | `wall` | 2.0 mm | Grosor de pared del barril. |
| Adaptador y Collar | `plate_dia` | 90 mm | Diámetro del anillo adaptador. |
| Adaptador y Collar | `bolt_circle` | 60 mm | Círculo de pernos de montaje. |
| Adaptador y Collar | `bolt_dia` | 4.5 mm | Holgura del perno (M4). |
| Adaptador y Collar | `hole_count` | 3 | Número de pernos de montaje. |
| Adaptador y Collar | `offset` | 3.0 mm | Radio que añade el collar. |

## Presets

- **Casquillo Guía 1/2 pulg** — el casquillo de media pulgada de uso diario.
- **Adaptador de Base Universal** — ajusta la brida estándar a cualquier
  fresadora.
- **Collar de 3 mm** — un desplazamiento fijo de 3 mm entre plantilla y corte.

## Perfil de Hiperobjeto

- **Dominio:** industrial
- **Interfaces CDG:**
  - **Brida de Casquillo Universal** (`socket`, casquillo de router — Porter-Cable
    universal, brida de 1-3/8 in) — la interfaz, definida por `barrel`,
    `barrel_len`, `wall`. Un clúster nuevo (ningún miembro de familia existente
    comparte aún el estándar de casquillo de router).
  - **Círculo de Pernos de Base** (`bolt_pattern`, internal) — `bolt_circle`,
    `bolt_dia`, `hole_count`.
- **Conciencia de material:** `tolerance_by_material` con `wall` y `bit_clear`
  adaptan un casquillo a una broca y desplazamiento específicos.
- **Licencia commons:** CERN-OHL-W-2.0
