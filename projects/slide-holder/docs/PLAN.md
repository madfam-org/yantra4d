# Slide Holder v2 — Remake Plan

> **Status**: Draft
> **Date**: 2026-02-16
> **Replaces**: `yantra4d_slide_holder.scad` (vendor wrapper for Lucas Wilder / MTU design)
> **Reference**: `docs/RESEARCH.pdf` — *Parametric Architectures for Microscope Slide Retention*

---

## 1. Motivation

The current slide-holder project is a thin wrapper around a vendor design that implements a single geometry — a basic vertical slotted box with rectangular ribs and no tolerance engineering. It hard-codes a single slide class (US 76.2x25mm) and provides no support for the diverse retention architectures required by different laboratory workflows (drying, staining, archival storage, transport).

The RESEARCH.pdf analysis identifies **four fundamental retention classes** and **five slide dimension classes** governed by ISO 8037 standards. This remake implements the research findings as a first-class multi-mode parametric OpenSCAD project, removing all vendor dependencies.

## 2. Architecture Overview

### 2.1 Four Retention Classes → Four Modes

Each retention class maps to a Yantra4D **mode** with its own SCAD file and renderable parts.

| Mode ID | Label | Class | SCAD File | Parts | Description |
|---------|-------|-------|-----------|-------|-------------|
| `tray` | Horizontal Tray | I | `tray.scad` | `tray` | Flat recessed pockets with anti-capillary ribs and finger notches. For slide reading, drying, consultation. |
| `box` | Storage Box | II | `box.scad` | `box_base`, `box_lid` | Vertical slotted box with tapered ribs, chamfered lead-ins, snap-fit lid. The classic "100-place" archival form. |
| `staining_rack` | Staining Rack | III | `staining_rack.scad` | `rack` | Skeletonized open frame with knife-edge rails and drainage angles for fluid immersion workflows. |
| `cabinet_drawer` | Cabinet Drawer | IV | `cabinet_drawer.scad` | `drawer`, `shell` | Sliding drawer with T-slot rails inside a stackable shell. For high-density archival systems. |

### 2.2 Five Slide Classes → Dropdown Preset

The `slide_standard` dropdown selects from ISO 8037 and common regional variants. Selecting a standard auto-populates `slide_length`, `slide_width`, and `slide_thickness`. Selecting "Custom" unlocks all three for manual override.

| Standard | Length (mm) | Width (mm) | Thickness (mm) | Application |
|----------|:----------:|:---------:|:-------------:|-------------|
| `iso` (default) | 76.0 | 26.0 | 1.0 | General histology |
| `us` | 76.2 | 25.4 | 1.0 | US "3x1 inch" standard |
| `petrographic` | 46.0 | 27.0 | 1.2 | Geology / thin sections |
| `supa_mega` | 75.0 | 50.0 | 1.0 | Brain / prostate sections |
| `custom` | (unlocked) | (unlocked) | (unlocked) | Manual entry |

**Key insight from research**: Clipped-corner slides (75x25, 45 deg clip) exist. Retention mechanisms must grip long edges or bottom face — never rely on corners for registration.

### 2.3 Shared Geometry Library

A shared include file `slide_lib.scad` provides reusable sub-modules used across all four modes:

| Module | Purpose |
|--------|---------|
| `slide_bounding_box(l, w, t, tol_xy, tol_z)` | Keep-out zone for a slide + tolerance |
| `retention_rib(height, root_w, tip_w, chamfer)` | Single tapered rib with chamfered lead-in |
| `slot_array(n, pitch, rib_module)` | Linear array of ribs at calculated pitch |
| `anti_capillary_ribs(length, width)` | Two floor rails at 25%/75% of pocket width |
| `finger_notch(radius, depth)` | Cylindrical boolean for ergonomic slide removal |
| `stacking_lip(length, width, height, chamfer)` | Perimeter ridge + groove for vertical stacking |
| `label_recess(width, height, depth)` | Debossed label area for indexing |

## 3. Parameter Hierarchy

### 3.1 Global Parameters (all modes)

These parameters appear in every mode.

| Parameter | Type | Default | Range | Group | Description |
|-----------|------|---------|-------|-------|-------------|
| `slide_standard` | dropdown | `iso` | iso/us/petrographic/supa_mega/custom | Slide | Slide dimension standard (ISO 8037) |
| `slide_length` | slider | 76.0 | 40–100, step 0.1 | Slide | Slide length in mm |
| `slide_width` | slider | 26.0 | 15–55, step 0.1 | Slide | Slide width in mm |
| `slide_thickness` | slider | 1.0 | 0.5–2.0, step 0.1 | Slide | Slide thickness in mm |
| `num_slots` | slider | 25 | 1–100, step 1 | Architecture | Number of slide positions |
| `tolerance_xy` | slider | 0.4 | 0.1–1.0, step 0.05 | Tolerance | XY clearance for FDM printing |
| `tolerance_z` | slider | 0.2 | 0.05–0.5, step 0.05 | Tolerance | Z (thickness) clearance |
| `wall_thickness` | slider | 2.0 | 1.2–4.0, step 0.2 | Structure | Outer wall thickness |
| `label_area` | checkbox | true | — | Features | Generate debossed label recess |
| `fn` | slider | 0 | 0–64, step 8 | Quality | Resolution ($fn), 0 = auto |

### 3.2 Mode-Specific Parameters

#### Tray (Class I)

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `tray_columns` | slider | 5 | 1–10 | Columns of slide pockets |
| `tray_rows` | slider | 2 | 1–5 | Rows of slide pockets |
| `finger_notch` | checkbox | true | — | Generate finger notch per pocket |
| `anti_capillary` | checkbox | true | — | Generate anti-capillary floor ribs |

#### Box (Class II)

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `rib_profile` | dropdown | `tapered` | tapered/rectangular | Rib cross-section |
| `rib_width` | slider | 1.5 | 0.8–3.0, step 0.1 | Rib root width in mm |
| `density` | dropdown | `working` | archival/working/staining/mailer | Pitch preset (2.6/3.5/5.0/6.0 mm) |
| `lid_latch` | dropdown | `snap` | snap/magnetic/none | Lid closure mechanism |
| `stackable` | checkbox | true | — | Generate stacking lip + groove |
| `numbering_start` | slider | 1 | 0–999 | First slot number for debossed labels |

#### Staining Rack (Class III)

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `handle` | checkbox | true | — | Generate folding handle |
| `drainage_angle` | slider | 5 | 0–15, step 1 | Drainage slope in degrees |
| `open_bottom` | checkbox | true | — | Crossbar floor vs. solid floor |

#### Cabinet Drawer (Class IV)

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `rail_profile` | dropdown | `t_slot` | t_slot/l_rail | Drawer rail cross-section |
| `backstop` | checkbox | true | — | Flexible tab prevents full extraction |
| `drawers_per_shell` | slider | 5 | 1–10 | Number of drawer slots in shell |

## 4. Derived Dimensions (computed in SCAD)

These are not user-facing parameters — they're calculated from the inputs above. Documented here so the engineering logic is traceable to RESEARCH.pdf.

| Variable | Formula | Source |
|----------|---------|--------|
| `slot_width` | `slide_thickness + tolerance_z + 0.2` (waviness compensation) | RESEARCH 2.1.2 |
| `slot_depth` | `slide_width / 2` to `slide_width` (mode-dependent) | RESEARCH Table 1 |
| `pitch` | `slot_width + rib_width` | RESEARCH 5.1.2 |
| `body_width` | `(num_slots * pitch) + (2 * wall_thickness)` | Derived |
| `body_depth` | `slide_length + (2 * wall_thickness) + tolerance_xy` | Derived |
| `rib_tip_width` | `rib_width * 0.6` (tapered) or `rib_width` (rectangular) | RESEARCH 5.1.1 |
| `chamfer_height` | `min(2.0, rib_height * 0.15)` | RESEARCH 5.1.1 |
| `anti_cap_offset` | `slide_width * 0.25` (placed at 25% and 75%) | RESEARCH 4.1 |
| `finger_radius` | `max(8, slide_width * 0.35)` | RESEARCH 4.2 |

## 5. Constraints

| Expression | Level | Message |
|-----------|-------|---------|
| `num_slots >= 1` | error | At least 1 slide slot required |
| `slide_thickness > 0` | error | Slide thickness must be positive |
| `slide_length > slide_width` | error | Length must exceed width |
| `wall_thickness >= 1.2` | warning | Walls below 1.2mm may not print reliably (3 perimeters at 0.4mm nozzle) |
| `num_slots > 50` | warning | More than 50 slots may exceed typical print bed width |
| `tolerance_xy < 0.2` | warning | Tolerance below 0.2mm may cause insertion difficulty |
| `slide_standard == "supa_mega" && density == "archival"` | warning | Supa Mega slides at archival density require very wide print bed |

## 6. Presets

| Name | Slide Standard | num_slots | Mode-Specific | Use Case |
|------|---------------|-----------|---------------|----------|
| **Standard 25-Place Box** | iso | 25 | density=working, lid_latch=snap | General lab storage |
| **100-Place Archival** | iso | 100 | density=archival, stackable=true | Long-term archival |
| **Petrographic Box** | petrographic | 20 | density=working | Geology thin sections |
| **Drying Tray (10)** | iso | 10 | tray: 5x2, anti_capillary=true | Post-staining drying |
| **20-Slide Staining Rack** | iso | 20 | handle=true, drainage_angle=5 | Coplin jar staining |
| **Compact 5-Slide** | us | 5 | density=working, stackable=false | Quick bench reference |
| **Supa Mega Tray** | supa_mega | 4 | tray: 2x2, finger_notch=true | Large tissue sections |
| **Cabinet Unit (5 drawers)** | iso | 25 | drawers=5, rail=t_slot | High-density archival |

## 7. File Structure After Remake

```
projects/slide-holder/
  project.json                  # Manifest (4 modes, full parameter set)
  slide_lib.scad                # Shared geometry modules
  tray.scad                     # Class I — Horizontal Planar
  box.scad                      # Class II — Vertical Slotted (base + lid)
  staining_rack.scad            # Class III — Kinematic Fluid
  cabinet_drawer.scad           # Class IV — High-Density Archival (drawer + shell)
  docs/
    README.md                   # Auto-generated from project.json
    RESEARCH.pdf                # Engineering analysis (unchanged)
    PLAN.md                     # This document
  exports/                      # Reference STLs (generated after implementation)
```

**Removed**: `vendor/` directory, `yantra4d_slide_holder.scad` (replaced by the four mode files above).

## 8. Implementation Phases

### Phase 1: Foundation + Class II Box (MVP)

**Goal**: Replace current design with a functional multi-slide-class box that's strictly better than the vendor wrapper.

1. **Create `slide_lib.scad`** — `slide_bounding_box()`, `retention_rib()`, `slot_array()`, `stacking_lip()`, `label_recess()`
2. **Create `box.scad`** — Vertical slotted box with:
   - Tapered rib profiles with 45-deg chamfered lead-in (RESEARCH 5.1.1)
   - Pitch auto-calculated from density preset (RESEARCH 5.1.2)
   - Separate `box_base` and `box_lid` parts (render_mode dispatch)
   - Snap-fit cantilever latch (15mm arm length for PLA, RESEARCH 5.3)
   - Optional stacking lip + groove (RESEARCH 4.4)
   - Optional debossed numbering (draft_mode suppresses text, RESEARCH 8.3)
3. **Update `project.json`** — Single mode `box` initially, full parameter set for slide class + box architecture
4. **Delete `vendor/`** and old `yantra4d_slide_holder.scad`
5. **Render reference STLs** for "Standard 25-Place Box" preset

### Phase 2: Class I Horizontal Tray

1. **Create `tray.scad`** — Horizontal planar system with:
   - Recessed pockets with anti-capillary floor ribs (2mm wide, 0.5mm high, at 25%/75% of pocket width, RESEARCH 4.1)
   - Cylindrical finger notches (15-22mm width, RESEARCH 4.2)
   - Grid layout (rows x columns)
2. **Add `tray` mode to `project.json`**
3. **Add tray-specific parameters** (`tray_columns`, `tray_rows`, `finger_notch`, `anti_capillary`)

### Phase 3: Class III Staining Rack

1. **Create `staining_rack.scad`** — Kinematic fluid system with:
   - Skeletonized open frame (four corner pillars + slotted rails, RESEARCH 6.1)
   - Knife-edge rib profile (minimal contact with slide face)
   - Open crossbar bottom (not solid, RESEARCH 6.1)
   - All horizontal surfaces sloped at `drainage_angle` (>5 deg, RESEARCH 6.1)
   - Optional folding handle geometry (RESEARCH 6.2)
   - Pitch forced to >= 5.0mm (fluid dynamics constraint, RESEARCH 5.1.2)
2. **Add `staining_rack` mode to `project.json`**
3. **Add rack-specific parameters** (`handle`, `drainage_angle`, `open_bottom`)

### Phase 4: Class IV Cabinet Drawer

1. **Create `cabinet_drawer.scad`** — High-density archival system with:
   - Drawer body with vertical slots (reuses `slot_array` from slide_lib)
   - Shell with T-slot or L-rail profiles (RESEARCH 7.2)
   - Interlocking stack tabs on shell top/bottom (trapezoidal dovetail, RESEARCH 7.1)
   - Flexible rear backstop tab (RESEARCH 7.2)
   - Structural ribbing on shell walls (RESEARCH 7.3)
   - Wall thickness >= 2.4mm default (RESEARCH 7.3)
2. **Add `cabinet_drawer` mode to `project.json`**
3. **Add cabinet-specific parameters** (`rail_profile`, `backstop`, `drawers_per_shell`)

## 9. Manifest Changes Summary

| Field | Current (v0.1.0) | After Remake (v2.0.0) |
|-------|------------------|----------------------|
| version | 0.1.0 | 2.0.0 |
| modes | 1 (holder) | 4 (tray, box, staining_rack, cabinet_drawer) |
| parameters | 5 (slides, thickness, length, width, fn) | ~20 (slide class, tolerances, architecture, features) |
| parameter types | sliders only | sliders + dropdowns + checkboxes |
| presets | 5 (single mode) | 8+ (across all modes) |
| parts | 1 (holder) | 7 (tray, box_base, box_lid, rack, drawer, shell) |
| constraints | 4 | 7+ |
| materials | 2 (PLA, PETG) | 4+ (PLA, PETG, ABS/ASA, Nylon — per RESEARCH Table 3) |
| difficulty | beginner | intermediate |

## 10. Engineering Reference Tables

Carried forward from RESEARCH.pdf for quick implementation reference.

### Table A: Recommended Slot Clearances

| Slide Type | Slot Width (mm) | Includes |
|-----------|:--------------:|----------|
| ISO Standard (1.0-1.2mm thick) | 1.6 | tolerance_z + waviness |
| Petrographic (1.2-1.5mm thick) | 1.9 | tolerance_z + waviness |
| Supa Mega (1.0-1.2mm thick) | 1.6 | tolerance_z + waviness |
| Economy/Thin (0.8-1.0mm thick) | 1.4 | tolerance_z + waviness |

### Table B: Pitch by Application

| Application | Rib Width (mm) | Pitch (mm) | Access Method |
|-------------|:-------------:|:---------:|---------------|
| Archival Box | 1.0 | 2.6 | Tweezers only |
| Working Box | 1.5 | 3.5 | Finger access |
| Staining Rack | 2.0 | 5.0 | Prevents capillary bridging |
| Mailer | 3.0 | 6.0 | Impact resistance |

### Table C: Material Compatibility

| Material | Xylene | Alcohol | Heat Deflection | Recommended For |
|----------|:------:|:------:|:--------------:|-----------------|
| PLA | Low (deforms) | High | 50 deg C | Dry storage only (tray, box) |
| PETG | High | High | 70 deg C | General purpose, short-term staining |
| ABS/ASA | Fail (dissolves) | High | 95 deg C | Archival, high-temp drying |
| Nylon (PA) | High | High | 100 deg C+ | Heavy-duty staining, moving parts |
| TPU | Variable | High | N/A | Liners, bumpers, seals |

## 11. Testing Strategy

| Test | Method | Acceptance |
|------|--------|-----------|
| All modes render | `POST /api/render` with each mode's default preset | HTTP 200, valid STL |
| Slide class switching | Render box mode with iso, us, petrographic, supa_mega | All produce valid geometry |
| Tolerance boundaries | Render with tolerance_xy=0.1 and tolerance_xy=1.0 | No degenerate geometry |
| High slot count | Render box with num_slots=100 | Completes within 300s timeout |
| STL verification | `POST /api/verify` per mode | Watertight, body_count matches parts |
| Manifest validation | JSON Schema check against `packages/schemas/project-manifest.schema.json` | Passes |
| Studio rendering | Load slide-holder in studio, switch modes, adjust params | No JS errors, 3D preview updates |

## 12. Open Questions

1. **Lid hinge method**: Snap-fit only for Phase 1, or also pinned hinge (requires filament axle)? Recommend snap-fit only for v2.0 — simpler single-material print.
2. **Cabinet drawer rail clearance**: T-slot tolerance needs physical testing. Default to `tolerance_xy + 0.1mm` extra.
3. **Staining rack handle**: Generate as part of main body (non-functional sculpture) or as separate articulated part? Recommend integrated non-moving handle for v2.0, articulated in future version.
4. **Text rendering performance**: Debossed numbering on 100-slot boxes is slow in OpenSCAD. The `draft_mode` / `fn=0` setting should suppress text. Wire this to the existing `fn` parameter or add a separate `draft_mode` checkbox?

---

*This plan derives directly from the engineering analysis in `RESEARCH.pdf`. All section numbers, dimensions, and material data reference that document.*
