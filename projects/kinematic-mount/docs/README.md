# Kinematic Mount 3-Ball / Soporte Cinemático de 3 Bolas

A repeatable 3-ball kinematic coupling — Kelvin (cone/vee/flat) and Maxwell
(three radial vees) bases plus a ball-cup top plate, built CadQuery-first for
Yantra4D.

---

## English

Two plates that mate on exactly **six points of contact** separate and re-seat
to the same position every time. This is how optics, fixtures and tool changers
get repeatability without dowel pins.

### Modes

| Mode | Part | What it is |
|------|------|-----------|
| **Kelvin Base (Cone/Vee/Flat)** | `base_plate` | Three *different* seats at 120°: a trihedral cone (3 contacts), a radial vee (2 contacts), a flat land (1 contact) = 6 constraints. |
| **Maxwell Base (3 Radial Vees)** | `base_vee3` | Three *identical* V-grooves radiating from the centre at 120° — six contacts, lower thermal sensitivity. |
| **Top Plate (Ball Cups)** | `top_plate` | Three spherical cups at 120° that cradle pressed/glued steel balls, which seat into either base. |

### Real dimensions

- **Three seats / balls at 120°** on a bolt-circle (`bolt_circle`, default
  40 mm).
- **Ball diameter 6–10 mm** — steel bearing balls, **NOT printed**. Default
  8 mm; the cone, vee and cups all scale to it.
- Each seat is a **cut pocket** so the ball contacts the seat *walls* (cone: a
  90° trihedral cone, vee: a 90° radial groove), never the pocket floor. The
  flat land is a true 1-point rest.

### Six-point constraint (why it repeats)

Cone 3 + vee 2 + flat 1 = **6** = the six rigid-body degrees of freedom, so the
mate is *exactly* constrained — no over-constraint, no slop. The Maxwell base
reaches the same six via three symmetric 2-point vees.

### Parameters

- `plate_dia`, `plate_thick`, `center_bore` — the plate blank.
- `ball_dia`, `bolt_circle` — the kinematic interface. Set `ball_dia` to your
  bearing balls.
- `mount_bolt_d` — the three mount bolts (placed *between* the seats).

### Printing notes

Print both plates in the **same material at ≥40% infill** (PETG or PLA) so they
scale alike and the seats don't creep. Press or epoxy precision bearing balls
into the top cups. If your printer over-extrudes, deburr the cone/vee flanks so
the ball touches the walls and does not bottom out. All three modes are
watertight and single-body across the range: every seat is a cut pocket, and the
centre bore and mount holes vent through the plate — no trapped voids, no tangent
sphere seams.

---

## Español

Dos placas que se acoplan en exactamente **seis puntos de contacto** se separan
y reasientan en la misma posición cada vez. Así consiguen repetibilidad la
óptica, el utillaje y los cambiadores de herramienta sin pasadores.

### Modos

| Modo | Pieza | Qué es |
|------|-------|--------|
| **Base Kelvin (Cono/Uve/Plano)** | `base_plate` | Tres asientos *distintos* a 120°: cono triédrico (3 contactos), uve radial (2), plano (1) = 6 restricciones. |
| **Base Maxwell (3 Uves Radiales)** | `base_vee3` | Tres ranuras en uve *idénticas* radiando desde el centro a 120° — seis contactos, menor sensibilidad térmica. |
| **Placa Superior (Casquetes)** | `top_plate` | Tres casquetes esféricos a 120° que alojan bolas de acero prensadas/pegadas. |

### Dimensiones reales

- **Tres asientos / bolas a 120°** sobre un círculo (`bolt_circle`, 40 mm por
  defecto).
- **Diámetro de bola 6–10 mm** — bolas de acero, **NO se imprimen**. 8 mm por
  defecto; cono, uve y casquetes se escalan a ella.
- Cada asiento es un **hueco cortado** para que la bola toque las *paredes*
  (cono a 90°, uve radial a 90°), nunca el fondo. El plano es un apoyo de 1
  punto.

### Restricción de seis puntos

Cono 3 + uve 2 + plano 1 = **6** = los seis grados de libertad de sólido rígido,
así que el acople queda *exactamente* restringido, sin holgura ni
sobre-restricción.

### Parámetros

- `plate_dia`, `plate_thick`, `center_bore` — la placa.
- `ball_dia`, `bolt_circle` — la interfaz cinemática.
- `mount_bolt_d` — los tres pernos de montaje (entre los asientos).

### Notas de impresión

Imprime ambas placas en el **mismo material con ≥40% de relleno** (PETG o PLA).
Presiona o pega bolas de precisión en los casquetes. Rebaba los flancos si tu
impresora sobre-extruye. Los tres modos son estancos y de cuerpo único; cada
asiento es un hueco cortado y el barreno central y los agujeros ventilan a
través de la placa — sin huecos atrapados ni costuras esféricas tangentes.

---

**License / Licencia:** CERN-OHL-W-2.0
