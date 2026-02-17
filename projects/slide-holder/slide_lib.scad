// ============================================================================
// slide_lib.scad — Shared Geometry Library for Microscope Slide Retention
// ============================================================================
// Reference: docs/RESEARCH.pdf — "Parametric Architectures for Microscope
//            Slide Retention" (ISO 8037 tolerance fields, FDM constraints)
//
// This file is `use`d by all four mode SCAD files (box, tray, staining_rack,
// cabinet_drawer). It provides the common-denominator geometry primitives
// identified in the research analysis.
// ============================================================================

// ---------------------------------------------------------------------------
// 1. Slide Standard Lookup (RESEARCH §2)
// ---------------------------------------------------------------------------
// Index: 0=ISO, 1=US, 2=Petrographic, 3=Supa Mega
// Each row: [length, width, thickness]
SLIDE_STANDARDS = [
    [76.0, 26.0, 1.0],   // ISO 8037 standard
    [76.2, 25.4, 1.0],   // US "3x1 inch"
    [46.0, 27.0, 1.2],   // Petrographic (geology)
    [75.0, 50.0, 1.0],   // Supa Mega (brain/prostate)
];

// Resolve effective slide dimensions from standard index + custom overrides
function resolve_slide(standard, custom_l, custom_w, custom_t) =
    standard < len(SLIDE_STANDARDS)
        ? SLIDE_STANDARDS[standard]
        : [custom_l, custom_w, custom_t];

// ---------------------------------------------------------------------------
// 2. Density / Pitch Lookup (RESEARCH §5.1.2, Table B)
// ---------------------------------------------------------------------------
// Index: 0=archival, 1=working, 2=staining, 3=mailer
// Each row: [rib_width_mm, description]
DENSITY_RIB_WIDTHS = [1.0, 1.5, 2.0, 3.0];

// Accessor function for use<> compatibility (use<> imports functions, not variables)
function density_rib_width(idx) = DENSITY_RIB_WIDTHS[idx];

// Compute slot width from slide thickness + tolerances + waviness
// RESEARCH §2.1.2: 0.2mm waviness compensation for ISO 8037 planarity spec
function slot_width(slide_thick, tol_z) =
    slide_thick + tol_z + 0.2;

// Compute pitch (center-to-center distance between slides)
function pitch(slot_w, rib_w) = slot_w + rib_w;

// ---------------------------------------------------------------------------
// 3. Slide Bounding Box (RESEARCH §8.2)
// ---------------------------------------------------------------------------
// The keep-out zone for a single slide including clearances.
// Used for Boolean subtraction in all retention classes.
module slide_bounding_box(length, width, thickness, tol_xy, tol_z) {
    cube([
        thickness + tol_z + 0.2,   // waviness compensation
        length + tol_xy,
        width + tol_xy
    ]);
}

// ---------------------------------------------------------------------------
// 4. Retention Rib — Tapered with Chamfered Lead-In (RESEARCH §5.1.1)
// ---------------------------------------------------------------------------
// A single rib separating two slide slots. Tapered profile is wider at the
// base (root) and narrower at the tip for a funnel effect during insertion.
// The top 1-2mm features a 45° chamfer to guide slides in.
//
// Profile (XZ cross-section, extruded along Y):
//
//       ╱tip_w╲       ← chamfer zone (45°)
//      │       │
//      │       │      ← main body
//     ╱         ╲
//    root_width        ← base
//
module retention_rib(height, depth, root_w, tip_w, chamfer_h) {
    _chamfer = min(chamfer_h, height * 0.25);
    _body_h = height - _chamfer;
    _taper_offset = (root_w - tip_w) / 2;

    // Profile is drawn in XY then rotated so:
    //   X → rib width (pitch direction)
    //   Y → rib height, rotated to Z (vertical)
    //   extrusion → rotated from Z to Y (slide-insertion direction)
    rotate([-90, 0, 0])
    translate([0, -height, 0]) {
        // Main tapered body
        linear_extrude(height = depth)
            polygon([
                [0, 0],
                [root_w, 0],
                [root_w - _taper_offset, _body_h],
                [_taper_offset, _body_h]
            ]);

        // Chamfered lead-in at top
        if (_chamfer > 0) {
            _cw = (root_w - 2 * _taper_offset);  // width at body top = tip_w
            translate([_taper_offset, 0, 0])
                linear_extrude(height = depth)
                    polygon([
                        [0, _body_h],
                        [_cw, _body_h],
                        [_cw / 2 + _cw * 0.3, _body_h + _chamfer],
                        [_cw / 2 - _cw * 0.3, _body_h + _chamfer]
                    ]);
        }
    }
}

// Rectangular rib (simpler, for archival density)
module rectangular_rib(height, depth, width) {
    cube([width, depth, height]);
}

// ---------------------------------------------------------------------------
// 5. Slot Array (RESEARCH §8.2)
// ---------------------------------------------------------------------------
// Linear array of ribs along the X axis at the computed pitch.
// Uses additive (union) approach — cleaner for tapered ribs per RESEARCH §8.2.
module slot_array(count, pitch, height, depth, root_w, tip_w, chamfer_h, tapered) {
    for (i = [0 : count]) {
        translate([i * pitch, 0, 0]) {
            if (tapered) {
                retention_rib(height, depth, root_w, tip_w, chamfer_h);
            } else {
                rectangular_rib(height, depth, root_w);
            }
        }
    }
}

// ---------------------------------------------------------------------------
// 6. Anti-Capillary Floor Ribs (RESEARCH §4.1)
// ---------------------------------------------------------------------------
// Two parallel rails at 25% and 75% of pocket width to break vacuum seal.
// Dimensions: 2.0mm wide, 0.5-1.0mm high per research.
module anti_capillary_ribs(pocket_length, pocket_width, rib_height = 0.5) {
    _rib_w = 2.0;
    _offset_25 = pocket_width * 0.25 - _rib_w / 2;
    _offset_75 = pocket_width * 0.75 - _rib_w / 2;

    // Rail at 25%
    translate([_offset_25, 0, 0])
        cube([_rib_w, pocket_length, rib_height]);

    // Rail at 75%
    translate([_offset_75, 0, 0])
        cube([_rib_w, pocket_length, rib_height]);
}

// ---------------------------------------------------------------------------
// 7. Finger Notch (RESEARCH §4.2)
// ---------------------------------------------------------------------------
// Cylindrical Boolean subtraction for ergonomic slide removal.
// Width 15-22mm per commercial holder research (Abdos, Globe Scientific).
// Depth extends below floor for finger pad access.
module finger_notch(radius, depth) {
    translate([0, 0, -depth / 2])
        cylinder(r = radius, h = depth + 1, $fn = 32);
}

// ---------------------------------------------------------------------------
// 8. Stacking Lip and Groove (RESEARCH §4.4)
// ---------------------------------------------------------------------------
// Perimeter ridge on top + groove on bottom for stable vertical stacking.
// Lip: 3mm high, 45° chamfer per research.
module stacking_lip(outer_x, outer_y, lip_h = 3, lip_w = 1.5) {
    difference() {
        // Outer ridge
        linear_extrude(height = lip_h)
            difference() {
                square([outer_x, outer_y]);
                offset(delta = -lip_w)
                    square([outer_x, outer_y]);
            }

        // 45° outer chamfer
        translate([0, 0, lip_h])
            rotate([0, 0, 0])
                linear_extrude(height = lip_w, scale = [
                    (outer_x + 2 * lip_w) / outer_x,
                    (outer_y + 2 * lip_w) / outer_y
                ])
                    translate([-lip_w, -lip_w])
                        square([outer_x + 2 * lip_w, outer_y + 2 * lip_w]);
    }
}

// Groove (on bottom of part above) — slightly wider for clearance
module stacking_groove(outer_x, outer_y, groove_h = 3.2, groove_w = 1.7) {
    linear_extrude(height = groove_h)
        difference() {
            square([outer_x, outer_y]);
            offset(delta = -groove_w)
                square([outer_x, outer_y]);
        }
}

// ---------------------------------------------------------------------------
// 9. Label Recess (RESEARCH §8.3)
// ---------------------------------------------------------------------------
// Debossed flat area for handwritten or printed labels.
// Engraved 0.4mm deep per research (embossed interferes with insertion).
module label_recess(width, height, depth = 0.4) {
    cube([width, height, depth]);
}

// ---------------------------------------------------------------------------
// 10. Snap-Fit Cantilever Latch (RESEARCH §5.3)
// ---------------------------------------------------------------------------
// Flexible arm on lid engages lip on base. For PLA, arm length >= 15mm
// to stay within yield stress limits.
//
// Hook profile (side view):
//    ┌──╮
//    │  │ ← hook
//    │  │
//    │  │ ← arm (flexible)
//    └──┘ ← anchor
//
module snap_latch_arm(arm_length, arm_width, arm_thick, hook_height, hook_depth) {
    // Arm
    cube([arm_width, arm_thick, arm_length]);

    // Hook at end
    translate([0, 0, arm_length])
        cube([arm_width, arm_thick + hook_depth, hook_height]);
}

// The catch (lip on the base that the hook grabs)
module snap_latch_catch(width, height, depth) {
    cube([width, depth, height]);
}

// ---------------------------------------------------------------------------
// 11. Interlocking Stack Tab (RESEARCH §7.1)
// ---------------------------------------------------------------------------
// Trapezoidal dovetail for cabinet stacking stability.
// Male tab on top, female recess on bottom.
module stack_tab_male(base_w = 15, top_w = 10, height = 4, depth = 8) {
    _offset = (base_w - top_w) / 2;
    linear_extrude(height = depth)
        polygon([
            [0, 0],
            [base_w, 0],
            [base_w - _offset, height],
            [_offset, height]
        ]);
}

module stack_tab_female(base_w = 15, top_w = 10, height = 4, depth = 8, tol = 0.4) {
    _bw = base_w + tol;
    _tw = top_w + tol;
    _h = height + tol / 2;
    _offset = (_bw - _tw) / 2;
    linear_extrude(height = depth + tol)
        polygon([
            [0, 0],
            [_bw, 0],
            [_bw - _offset, _h],
            [_offset, _h]
        ]);
}

// ---------------------------------------------------------------------------
// 12. Drainage Slope (RESEARCH §6.1)
// ---------------------------------------------------------------------------
// Applies a drainage angle to horizontal surfaces for staining rack runoff.
module drainage_slope(length, width, height, angle) {
    _drop = length * tan(angle);
    polyhedron(
        points = [
            [0, 0, 0],
            [width, 0, 0],
            [width, length, 0],
            [0, length, 0],
            [0, 0, height],
            [width, 0, height],
            [width, length, height - _drop],
            [0, length, height - _drop]
        ],
        faces = [
            [0, 1, 2, 3],  // bottom
            [7, 6, 5, 4],  // top
            [0, 4, 5, 1],  // front
            [2, 6, 7, 3],  // back
            [0, 3, 7, 4],  // left
            [1, 5, 6, 2],  // right
        ]
    );
}
