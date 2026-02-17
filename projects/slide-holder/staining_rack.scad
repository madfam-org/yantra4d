// ============================================================================
// staining_rack.scad — Class III: Kinematic Fluid / Staining Rack
// ============================================================================
// Reference: docs/RESEARCH.pdf §6 (Kinematic Fluid Systems)
//
// Skeletonized open frame designed for slide immersion in staining solutions
// (Coplin jars, staining dishes). Features knife-edge ribs for minimal contact,
// open crossbar bottom for fluid circulation, and drainage-angled surfaces.
//
// Parts:
//   render_mode 0 → rack
// ============================================================================

use <slide_lib.scad>

// ---------------------------------------------------------------------------
// Parameters (injected by platform via -D)
// ---------------------------------------------------------------------------

// --- Slide Standard ---
slide_standard = 0;       // 0=ISO, 1=US, 2=Petrographic, 3=Supa Mega, 4=Custom
custom_slide_length = 76;
custom_slide_width = 26;
custom_slide_thickness = 1.0;

// --- Architecture ---
num_slots = 20;            // Number of slide positions

// --- Tolerances ---
tolerance_xy = 0.4;        // XY clearance (mm)
tolerance_z = 0.2;         // Z / thickness clearance (mm)

// --- Structure ---
wall_thickness = 2.0;      // Outer wall / pillar thickness (mm)

// --- Rack-specific ---
handle = 1;                // 1=generate carrying handle
drainage_angle = 5;        // Drainage slope in degrees
open_bottom = 1;           // 1=crossbar floor, 0=solid floor

// --- Features ---
label_area = 1;            // 1=generate debossed label recess

// --- Quality ---
fn = 0;                    // Resolution ($fn), 0 = auto

// --- Mode ---
render_mode = 0;           // 0=rack

// ---------------------------------------------------------------------------
// Resolution
// ---------------------------------------------------------------------------
$fn = fn > 0 ? fn : 32;

// ---------------------------------------------------------------------------
// Resolve Slide Dimensions
// ---------------------------------------------------------------------------
_slide = resolve_slide(slide_standard, custom_slide_length,
                       custom_slide_width, custom_slide_thickness);
_sl = _slide[0];   // slide length
_sw = _slide[1];   // slide width
_st = _slide[2];   // slide thickness

// ---------------------------------------------------------------------------
// Derived Dimensions (RESEARCH §6.1)
// ---------------------------------------------------------------------------

// Staining racks force minimum pitch for fluid dynamics (RESEARCH §5.1.2)
_min_rib_w = 2.0;
_slot_w = slot_width(_st, tolerance_z);
_pitch = pitch(_slot_w, _min_rib_w);
_forced_pitch = max(_pitch, 5.0);   // Minimum 5mm pitch for staining

// Slot depth: slides fully immersed, depth = slide_width
_slot_depth = _sw;
_rib_height = _slot_depth;

// Frame dimensions
_pillar_w = wall_thickness;
_crossbar_w = 3.0;    // crossbar width
_crossbar_h = 2.5;    // crossbar height

// Body envelope
_body_x = (num_slots * _forced_pitch) + _min_rib_w + (2 * _pillar_w);
_body_y = _sl + (2 * _pillar_w) + tolerance_xy;
_base_h = open_bottom == 1 ? _crossbar_h : wall_thickness;
_body_z = _rib_height + _base_h;

// Handle dimensions (RESEARCH §6.2)
_handle_w = min(_body_x * 0.6, 80);
_handle_h = 15;
_handle_thick = 4;

// ---------------------------------------------------------------------------
// rack — Skeletonized staining frame
// ---------------------------------------------------------------------------
module rack() {
    // --- Four corner pillars ---
    // Front-left
    cube([_pillar_w, _pillar_w, _body_z]);
    // Front-right
    translate([_body_x - _pillar_w, 0, 0])
        cube([_pillar_w, _pillar_w, _body_z]);
    // Back-left
    translate([0, _body_y - _pillar_w, 0])
        cube([_pillar_w, _pillar_w, _body_z]);
    // Back-right
    translate([_body_x - _pillar_w, _body_y - _pillar_w, 0])
        cube([_pillar_w, _pillar_w, _body_z]);

    // --- Top rails (connect pillars at the top) ---
    // Front rail
    translate([0, 0, _body_z - _crossbar_h])
        cube([_body_x, _pillar_w, _crossbar_h]);
    // Back rail
    translate([0, _body_y - _pillar_w, _body_z - _crossbar_h])
        cube([_body_x, _pillar_w, _crossbar_h]);
    // Left rail
    translate([0, 0, _body_z - _crossbar_h])
        cube([_pillar_w, _body_y, _crossbar_h]);
    // Right rail
    translate([_body_x - _pillar_w, 0, _body_z - _crossbar_h])
        cube([_pillar_w, _body_y, _crossbar_h]);

    // --- Bottom crossbars (open or solid) ---
    if (open_bottom == 1) {
        // Front and back bottom rails
        cube([_body_x, _pillar_w, _crossbar_h]);
        translate([0, _body_y - _pillar_w, 0])
            cube([_body_x, _pillar_w, _crossbar_h]);
        // Left and right bottom rails
        cube([_pillar_w, _body_y, _crossbar_h]);
        translate([_body_x - _pillar_w, 0, 0])
            cube([_pillar_w, _body_y, _crossbar_h]);
        // Two crossbars at 33% and 66% for slide support
        for (frac = [0.33, 0.66]) {
            translate([0, _body_y * frac - _crossbar_w / 2, 0])
                cube([_body_x, _crossbar_w, _crossbar_h]);
        }
    } else {
        // Solid floor with drainage slope
        if (drainage_angle > 0) {
            drainage_slope(_body_y, _body_x, wall_thickness, drainage_angle);
        } else {
            cube([_body_x, _body_y, wall_thickness]);
        }
    }

    // --- Slotted rib rails (knife-edge profile) ---
    // Front rib rail: sits on front bottom rail, extends up to rib height
    translate([_pillar_w, 0, _crossbar_h]) {
        for (i = [0 : num_slots]) {
            translate([i * _forced_pitch, 0, 0])
                rectangular_rib(_rib_height, _pillar_w, _min_rib_w);
        }
    }

    // Back rib rail (mirrors front)
    translate([_pillar_w, _body_y - _pillar_w, _crossbar_h]) {
        for (i = [0 : num_slots]) {
            translate([i * _forced_pitch, 0, 0])
                rectangular_rib(_rib_height, _pillar_w, _min_rib_w);
        }
    }

    // --- Handle (RESEARCH §6.2) ---
    if (handle == 1) {
        _hx = (_body_x - _handle_w) / 2;
        _hy = (_body_y - _handle_thick) / 2;
        _hz = _body_z;

        // Two uprights
        translate([_hx, _hy, _hz])
            cube([_handle_thick, _handle_thick, _handle_h]);
        translate([_hx + _handle_w - _handle_thick, _hy, _hz])
            cube([_handle_thick, _handle_thick, _handle_h]);

        // Crossbar
        translate([_hx, _hy, _hz + _handle_h - _handle_thick])
            cube([_handle_w, _handle_thick, _handle_thick]);
    }

    // --- Label recess on front pillar ---
    if (label_area == 1 && fn > 0) {
        _label_w = min(30, _body_x * 0.3);
        _label_h = min(8, _crossbar_h * 0.8);
        translate([(_body_x - _label_w) / 2, -0.01, (_crossbar_h - _label_h) / 2])
            rotate([90, 0, 0])
                translate([0, 0, -0.4])
                    label_recess(_label_w, _label_h, 0.5);
    }
}

// ---------------------------------------------------------------------------
// Render Mode Dispatch
// ---------------------------------------------------------------------------
if (render_mode == 0) {
    rack();
}
