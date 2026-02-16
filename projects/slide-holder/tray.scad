// ============================================================================
// tray.scad — Class I: Horizontal Planar Tray
// ============================================================================
// Reference: docs/RESEARCH.pdf §3 (Horizontal Planar Systems)
//
// Flat tray with recessed pockets arranged in a grid. Each pocket holds one
// slide lying flat, with anti-capillary floor ribs to break vacuum seal and
// cylindrical finger notches for ergonomic removal.
//
// Parts:
//   render_mode 0 → tray
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
num_slots = 10;            // Total slide count (rows x columns)

// --- Tolerances ---
tolerance_xy = 0.4;        // XY clearance (mm)
tolerance_z = 0.2;         // Z / thickness clearance (mm)

// --- Structure ---
wall_thickness = 2.0;      // Outer wall thickness (mm)

// --- Tray-specific ---
tray_columns = 5;          // Columns of slide pockets
tray_rows = 2;             // Rows of slide pockets
finger_notch = 1;          // 1=generate finger notch per pocket
anti_capillary = 1;        // 1=generate anti-capillary floor ribs

// --- Features ---
label_area = 1;            // 1=generate debossed label recess

// --- Quality ---
fn = 0;                    // Resolution ($fn), 0 = auto

// --- Mode ---
render_mode = 0;           // 0=tray

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
// Derived Dimensions (RESEARCH §3, §4.1, §4.2)
// ---------------------------------------------------------------------------

// Pocket dimensions: slide + tolerance + clearance
_pocket_l = _sl + tolerance_xy;
_pocket_w = _sw + tolerance_xy;
_pocket_d = _st + tolerance_z + 1.0;   // depth: slide thickness + clearance + recess

// Spacing between pockets
_gap = wall_thickness;

// Finger notch (RESEARCH §4.2: 15-22mm width, extends below floor)
_finger_r = max(8, _sw * 0.35);

// Body envelope
_body_x = (tray_columns * (_pocket_w + _gap)) + _gap;
_body_y = (tray_rows * (_pocket_l + _gap)) + _gap;
_body_z = _pocket_d + wall_thickness;

// Anti-capillary rib height (RESEARCH §4.1: 0.5-1.0mm)
_acr_h = 0.5;

// ---------------------------------------------------------------------------
// tray — Flat tray with recessed pockets
// ---------------------------------------------------------------------------
module tray() {
    difference() {
        // Solid base
        cube([_body_x, _body_y, _body_z]);

        // Pockets (grid of recesses)
        for (col = [0 : tray_columns - 1]) {
            for (row = [0 : tray_rows - 1]) {
                _px = _gap + col * (_pocket_w + _gap);
                _py = _gap + row * (_pocket_l + _gap);
                _pz = wall_thickness;

                // Pocket recess
                translate([_px, _py, _pz])
                    cube([_pocket_w, _pocket_l, _pocket_d + 1]);

                // Finger notch (cylindrical cutout at center-front of pocket)
                if (finger_notch == 1) {
                    translate([_px + _pocket_w / 2, _py + _pocket_l / 2, -0.01])
                        finger_notch(radius = _finger_r, depth = _body_z + 0.02);
                }
            }
        }

        // Label recess on front face
        if (label_area == 1) {
            _label_w = min(40, _body_x * 0.5);
            _label_h = min(10, _body_z * 0.5);
            translate([(_body_x - _label_w) / 2, -0.01, (_body_z - _label_h) / 2])
                rotate([90, 0, 0])
                    translate([0, 0, -0.4])
                        label_recess(_label_w, _label_h, 0.5);
        }
    }

    // Anti-capillary ribs inside each pocket (RESEARCH §4.1)
    if (anti_capillary == 1) {
        for (col = [0 : tray_columns - 1]) {
            for (row = [0 : tray_rows - 1]) {
                _px = _gap + col * (_pocket_w + _gap);
                _py = _gap + row * (_pocket_l + _gap);
                _pz = wall_thickness;

                translate([_px, _py, _pz])
                    anti_capillary_ribs(_pocket_l, _pocket_w, _acr_h);
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Render Mode Dispatch
// ---------------------------------------------------------------------------
if (render_mode == 0) {
    tray();
}
