# Dovetail Optics Slide / Corredera de Cola de Milano

A 60° dovetail translation slide for optics and light tooling — rail, sliding
carriage and locking carriage, built CadQuery-first for Yantra4D.

---

## English

The 60° prismatic dovetail is the de-facto open optical profile (Thorlabs
RC/XT class). Print the rail once and slide any number of carriers along it.

### Modes

| Mode | Part | What it is |
|------|------|-----------|
| **Dovetail Rail** | `rail` | The male dovetail track: a base plinth with a 60° dovetail ridge running its length and base bolt holes to fix it to a breadboard. |
| **Sliding Carriage** | `carriage` | A free-sliding block with a female-dovetail through-channel and a flat top platform carrying an M-bolt pattern for an optic, post or fixture. |
| **Locking Carriage** | `clamp` | Like the carriage, plus a gib slit and a cross clamp screw; tighten to pinch the rail flanks and lock the slide. |

### Real dimensions

- **60° included dovetail angle** — the lab-standard optical dovetail; each
  flank sits **30° off vertical**. Adjustable 45–75° via `dovetail_ang`.
- **Dovetail top width ≈ 20 mm** nominal (RC/XT-class optical rails run
  ~15–25 mm).
- The male rail is **wider at the base than the top** (the undercut), so a
  female carriage can only translate along the rail — it cannot lift off.
- Per-side sliding clearance `fit_clear` defaults to **0.30 mm**.

### Parameters

- `dovetail_w`, `dovetail_ang`, `rail_h` — the dovetail profile (shared by all
  three parts so they interoperate).
- `rail_len` — rail length (rail mode).
- `carriage_len`, `wall`, `bolt_d` — the carriage / clamp.
- `fit_clear` — the sliding fit. Set this first for a smooth slide.

### Printing notes

Print rail and carriage in the **same material** so shrinkage matches. Tune
`fit_clear` to your printer — 0.25 mm for a calibrated machine, 0.35–0.4 mm for
a loose one. Use **PETG or PLA at ≥30% infill** so the gib jaw is stiff enough
to clamp; a soft TPU carriage will not lock. All three modes are watertight and
single-body across the full parameter range: the female channel is open at both
ends and every bolt hole vents to a face, so there are no trapped voids.

---

## Español

La cola de milano prismática a 60° es el perfil óptico abierto de facto (clase
Thorlabs RC/XT). Imprime el riel una vez y desliza cuantos portadores quieras.

### Modos

| Modo | Pieza | Qué es |
|------|-------|--------|
| **Riel de Cola de Milano** | `rail` | La vía macho: un plinto base con cresta de cola de milano a 60° a lo largo y agujeros base para fijarlo a una placa. |
| **Carro Deslizante** | `carriage` | Un bloque de deslizamiento libre con canal pasante de cola de milano hembra y plataforma superior plana con patrón de tornillos M. |
| **Carro de Bloqueo** | `clamp` | Como el carro, más una ranura de gib y un tornillo transversal; apriétalo para bloquear la corredera. |

### Dimensiones reales

- **Ángulo incluido de 60°** — la cola de milano óptica estándar; cada flanco
  a **30° de la vertical**. Ajustable 45–75° con `dovetail_ang`.
- **Ancho superior de la cola de milano ≈ 20 mm** (los rieles ópticos clase
  RC/XT rondan 15–25 mm).
- El riel macho es **más ancho en la base que arriba** (el socavado), así que
  el carro hembra solo puede trasladarse — no puede levantarse.
- La holgura por lado `fit_clear` es **0.30 mm** por defecto.

### Parámetros

- `dovetail_w`, `dovetail_ang`, `rail_h` — el perfil de cola de milano.
- `rail_len` — longitud del riel (modo riel).
- `carriage_len`, `wall`, `bolt_d` — el carro / bloqueo.
- `fit_clear` — el ajuste deslizante. Configúralo primero.

### Notas de impresión

Imprime riel y carro en el **mismo material** para igualar la contracción.
Ajusta `fit_clear` a tu impresora. Usa **PETG o PLA con ≥30% de relleno** para
que la mordaza de gib apriete. Los tres modos son estancos y de cuerpo único en
todo el rango; el canal abre a ambos extremos y los agujeros ventilan a una
cara, sin huecos atrapados.

---

**License / Licencia:** CERN-OHL-W-2.0
