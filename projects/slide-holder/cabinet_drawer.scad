// ============================================================================
// cabinet_drawer.scad — Class IV: High-Density Archival Cabinet
// ============================================================================
// Reference: docs/RESEARCH.pdf §7 (High-Density Archival Systems)
//
// Sliding drawer with vertical slots inside a stackable shell. T-slot or
// L-rail profiles guide drawer insertion. Shell units interlock vertically
// with trapezoidal dovetail tabs.
//
// Parts:
//   render_mode 0 → drawer  (slide-holding tray that slides into shell)
//   render_mode 1 → shell   (outer housing with rail guides + stack tabs)
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
num_slots = 25;            // Number of slide positions per drawer
density = 0;               // 0=archival, 1=working, 2=staining, 3=mailer

// --- Tolerances ---
tolerance_xy = 0.4;        // XY clearance (mm)
tolerance_z = 0.2;         // Z / thickness clearance (mm)

// --- Structure ---
wall_thickness = 2.4;      // Outer wall thickness (mm) — RESEARCH §7.3 min 2.4
floor_thickness = 2.0;     // Floor thickness (mm)

// --- Cabinet-specific ---
rail_profile = 0;          // 0=t_slot, 1=l_rail
backstop = 1;              // 1=flexible tab prevents full extraction
drawers_per_shell = 5;     // Number of drawer slots in shell

// --- Features ---
label_area = 1;            // 1=generate debossed label recess

// --- Quality ---
fn = 0;                    // Resolution ($fn), 0 = auto

// --- Mode ---
render_mode = 0;           // 0=drawer, 1=shell

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
// Derived Dimensions (RESEARCH §7)
// ---------------------------------------------------------------------------
_rib_w = density_rib_width(density);
_slot_w = slot_width(_st, tolerance_z);
_pitch = pitch(_slot_w, _rib_w);

// Drawer slot depth: slides sit half-width deep
_slot_depth = _sw * 0.5;
_rib_height = _slot_depth;

// Drawer envelope
_drawer_x = (num_slots * _pitch) + _rib_w + (2 * 1.5);  // 1.5mm thin walls
_drawer_y = _sl + tolerance_xy + 4;    // slide length + front/back walls
_drawer_z = _rib_height + floor_thickness;

// Rail dimensions
_rail_h = 3.0;       // rail height
_rail_w = 3.0;       // rail width (T-slot head or L-rail shelf)
_rail_stem = 1.5;    // T-slot stem width
_rail_clearance = tolerance_xy + 0.1;   // RESEARCH §7.2 extra clearance

// Shell envelope (houses multiple drawers)
_shell_wall = wall_thickness;
_drawer_gap = 1.0;   // clearance between drawer and shell
_slot_h = _drawer_z + _drawer_gap + _rail_h;
// Shell X must encompass drawer + rails on each side + gaps + walls
_shell_x = _drawer_x + 2 * (_rail_w + _drawer_gap) + 2 * _shell_wall;
_shell_y = _drawer_y + _shell_wall + _drawer_gap + 5;  // extra at back for backstop
_shell_z = (drawers_per_shell * _slot_h) + _shell_wall * 2;

// Stack tab (RESEARCH §7.1)
_tab_base = 15;
_tab_top = 10;
_tab_h = 4;
_tab_depth = 8;
_tab_y = (_shell_y - _tab_depth) / 2;

// Backstop tab
_backstop_w = 10;
_backstop_h = _drawer_z * 0.6;
_backstop_t = 1.5;

// ---------------------------------------------------------------------------
// drawer — Slide-holding tray with rail flanges
// ---------------------------------------------------------------------------
module drawer() {
    // Base trough
    difference() {
        cube([_drawer_x, _drawer_y, _drawer_z]);

        // Hollow interior for slots
        translate([1.5, 1.5, floor_thickness])
            cube([
                _drawer_x - 3,
                _drawer_y - 3,
                _rib_height + 1
            ]);
    }

    // Rib array
    translate([1.5, 1.5, floor_thickness]) {
        slot_array(
            count = num_slots,
            pitch = _pitch,
            height = _rib_height,
            depth = _drawer_y - 3,
            root_w = _rib_w,
            tip_w = _rib_w * 0.7,
            chamfer_h = min(1.5, _rib_height * 0.1),
            tapered = true
        );
    }

    // Rail flanges along drawer sides
    if (rail_profile == 0) {
        // T-slot: stem + head
        // Left rail
        translate([-_rail_w, 0, _drawer_z / 2 - _rail_h / 2]) {
            // Stem
            cube([_rail_stem, _drawer_y, _rail_h]);
            // Head
            translate([-(_rail_w - _rail_stem) / 2, 0, _rail_h * 0.25])
                cube([_rail_w, _drawer_y, _rail_h * 0.5]);
        }
        // Right rail
        translate([_drawer_x, 0, _drawer_z / 2 - _rail_h / 2]) {
            cube([_rail_stem, _drawer_y, _rail_h]);
            translate([_rail_stem - (_rail_w - _rail_stem) / 2, 0, _rail_h * 0.25])
                cube([_rail_w, _drawer_y, _rail_h * 0.5]);
        }
    } else {
        // L-rail: simple shelf
        // Left rail
        translate([-_rail_w, 0, 0])
            cube([_rail_w, _drawer_y, _rail_h]);
        // Right rail
        translate([_drawer_x, 0, 0])
            cube([_rail_w, _drawer_y, _rail_h]);
    }

    // Front label recess
    if (label_area == 1) {
        _label_w = min(30, _drawer_x * 0.5);
        _label_h = min(8, _drawer_z * 0.5);
        translate([(_drawer_x - _label_w) / 2, -0.01, (_drawer_z - _label_h) / 2])
            rotate([90, 0, 0])
                translate([0, 0, -0.4])
                    label_recess(_label_w, _label_h, 0.5);
    }
}

// ---------------------------------------------------------------------------
// shell — Outer housing with rail channels and stack tabs
// ---------------------------------------------------------------------------
module shell() {
    // Position of drawer within shell
    _dx = _shell_wall + _drawer_gap + _rail_w;

    difference() {
        // Outer box
        cube([_shell_x, _shell_y, _shell_z]);

        // Drawer slot cavities
        for (d = [0 : drawers_per_shell - 1]) {
            _dz = _shell_wall + d * _slot_h;

            // Main drawer cavity (open at front)
            translate([_dx - _drawer_gap, -0.01, _dz])
                cube([
                    _drawer_x + _drawer_gap * 2,
                    _drawer_y + _drawer_gap,
                    _drawer_z + _drawer_gap
                ]);

            // Rail channels
            if (rail_profile == 0) {
                // T-slot channels
                // Left channel
                translate([_dx - _rail_w - _rail_clearance - _drawer_gap, -0.01, _dz + _drawer_z / 2 - _rail_h / 2 - _rail_clearance / 2]) {
                    cube([_rail_stem + _rail_clearance, _shell_y + 0.02, _rail_h + _rail_clearance]);
                    translate([-(_rail_w - _rail_stem) / 2 - _rail_clearance / 2, 0, _rail_h * 0.25 - _rail_clearance / 2])
                        cube([_rail_w + _rail_clearance, _shell_y + 0.02, _rail_h * 0.5 + _rail_clearance]);
                }
                // Right channel
                translate([_dx + _drawer_x + _drawer_gap, -0.01, _dz + _drawer_z / 2 - _rail_h / 2 - _rail_clearance / 2]) {
                    cube([_rail_stem + _rail_clearance, _shell_y + 0.02, _rail_h + _rail_clearance]);
                    translate([_rail_stem - (_rail_w - _rail_stem) / 2, 0, _rail_h * 0.25 - _rail_clearance / 2])
                        cube([_rail_w + _rail_clearance, _shell_y + 0.02, _rail_h * 0.5 + _rail_clearance]);
                }
            } else {
                // L-rail channels
                translate([_dx - _rail_w - _rail_clearance - _drawer_gap, -0.01, _dz - _rail_clearance / 2])
                    cube([_rail_w + _rail_clearance, _shell_y + 0.02, _rail_h + _rail_clearance]);
                translate([_dx + _drawer_x + _drawer_gap, -0.01, _dz - _rail_clearance / 2])
                    cube([_rail_w + _rail_clearance, _shell_y + 0.02, _rail_h + _rail_clearance]);
            }
        }

        // Female stack tab recesses on bottom
        translate([_shell_x * 0.25 - _tab_base / 2 - 0.2, _tab_y - 0.2, -0.01])
            stack_tab_female(_tab_base, _tab_top, _tab_h, _tab_depth);
        translate([_shell_x * 0.75 - _tab_base / 2 - 0.2, _tab_y - 0.2, -0.01])
            stack_tab_female(_tab_base, _tab_top, _tab_h, _tab_depth);
    }

    // Backstop tabs at rear (one per drawer slot)
    if (backstop == 1) {
        for (d = [0 : drawers_per_shell - 1]) {
            _dz = _shell_wall + d * _slot_h;
            translate([
                _shell_x / 2 - _backstop_w / 2,
                _shell_y - _shell_wall - _backstop_t,
                _dz
            ])
                cube([_backstop_w, _backstop_t, _backstop_h]);
        }
    }

    // Stack tabs — male on top

    translate([_shell_x * 0.25 - _tab_base / 2, _tab_y, _shell_z])
        stack_tab_male(_tab_base, _tab_top, _tab_h, _tab_depth);
    translate([_shell_x * 0.75 - _tab_base / 2, _tab_y, _shell_z])
        stack_tab_male(_tab_base, _tab_top, _tab_h, _tab_depth);

    // Label area on shell front (one per drawer slot)
    if (label_area == 1) {
        for (d = [0 : drawers_per_shell - 1]) {
            _dz = _shell_wall + d * _slot_h;
            _label_w = min(25, _shell_x * 0.3);
            _label_h = min(6, _slot_h * 0.3);
            translate([(_shell_x - _label_w) / 2, -0.01, _dz + (_slot_h - _label_h) / 2])
                rotate([90, 0, 0])
                    translate([0, 0, -0.4])
                        label_recess(_label_w, _label_h, 0.5);
        }
    }
}

// ---------------------------------------------------------------------------
// Render Mode Dispatch
// ---------------------------------------------------------------------------
if (render_mode == 0) {
    drawer();
}

if (render_mode == 1) {
    shell();
}
