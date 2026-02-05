# NEMA Motor Mount

Parametric NEMA motor mount with real motor preview using NopSCADlib

*Soporte parametrico para motores NEMA con vista previa del motor real usando NopSCADlib*

**Version**: 0.1.0  
**Slug**: `motor-mount`

## Modes

| ID | Label | SCAD File | Parts |
|---|---|---|---|
| `mount` | Mount | `qubic_mount.scad` | mount, nema_reference |

## Parameters

| Name | Type | Default | Range | Description |
|---|---|---|---|---|
| `nema_size` | slider | 17 | 17–34 (step 6) | NEMA motor size (17, 23, or 34) |
| `wall_thickness` | slider | 4 | 3–8 (step 0.5) | Thickness of mount walls |
| `base_thickness` | slider | 5 | 3–10 (step 0.5) | Thickness of the mount base plate |
| `mounting_style` | slider | 0 | 0–1 | Flat plate or L-bracket mount |
| `fn` | slider | 0 | 0–64 (step 8) | 0 = auto |

## Presets

- **NEMA 17 Standard**
  `nema_size`=17, `wall_thickness`=4, `base_thickness`=5, `mounting_style`=0
- **NEMA 17 Compact**
  `nema_size`=17, `wall_thickness`=3, `base_thickness`=4, `mounting_style`=0
- **NEMA 23 Standard**
  `nema_size`=23, `wall_thickness`=5, `base_thickness`=6, `mounting_style`=0
- **NEMA 23 Heavy Duty**
  `nema_size`=23, `wall_thickness`=6, `base_thickness`=8, `mounting_style`=0
- **NEMA 34 Standard**
  `nema_size`=34, `wall_thickness`=6, `base_thickness`=8, `mounting_style`=0

## Parts

| ID | Label | Default Color |
|---|---|---|
| `mount` | Mount | `#2c3e50` |
| `nema_reference` | NEMA Motor (reference) | `#34495e` |

## Constraints

- `wall_thickness >= 3` — Minimum 3mm thickness for structural rigidity (error)
- `base_thickness >= 3` — Base must be at least 3mm for screw support (error)

## Assembly Steps

1. **Print the mount**
   0.2mm layers, 50% infill for rigidity. PETG or ABS recommended
2. **Mount motor to bracket**
   Align holes and secure with 4 M3x10 screws
   Hardware: nema17_motor, m3_screw
3. **Secure mount to surface**
   Use base mounting holes with M5 bolts
   Hardware: m5_bolt

## Bill of Materials

| Item | Quantity | Unit |
|---|---|---|
| NEMA 17 Motor (42x42mm) | 1 | pcs |
| M3x10mm Screw (motor mounting) | 4 | pcs |
| M5 Bolt (base mounting) | 4 | pcs |

## Render Estimates

- **base_time**: 5
- **per_unit**: 2
- **per_part**: 8
- **fn_factor**: 48
- **wasm_multiplier**: 3
- **warning_threshold_seconds**: 60

---
*Auto-generated from `project.json` by `scripts/generate-project-docs.py`*
