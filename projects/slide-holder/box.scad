// ============================================================================
// box.scad — Class II: Vertical Slotted Storage Box
// ============================================================================
// Reference: docs/RESEARCH.pdf §5 (Vertical Slotted Systems)
//
// The classic "25-place" / "100-place" slide box. Slides stand vertically in
// parallel slots formed by tapered ribs with chamfered lead-ins.
//
// Parts:
//   render_mode 0 → box_base   (slotted trough + optional stacking lip)
//   render_mode 1 → box_lid    (snap-fit lid + optional stacking groove)
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
num_slots = 25;            // Number of slide positions
density = 1;               // 0=archival, 1=working, 2=staining, 3=mailer

// --- Tolerances ---
tolerance_xy = 0.4;        // XY clearance (mm)
tolerance_z = 0.2;         // Z / thickness clearance (mm)

// --- Structure ---
wall_thickness = 2.0;      // Outer wall thickness (mm)
floor_thickness = 2.0;     // Base floor thickness (mm)

// --- Box-specific ---
rib_profile = 0;           // 0=tapered, 1=rectangular
rib_width = 1.5;           // Rib root width (mm)
lid_latch = 0;             // 0=snap, 1=magnetic, 2=none
stackable = 1;             // 1=generate stacking lip/groove
numbering_start = 1;       // First slot number for debossed labels

// --- Features ---
label_area = 1;            // 1=generate debossed label recess

// --- Quality ---
fn = 0;                    // Resolution ($fn), 0 = auto

// --- Mode ---
render_mode = 0;           // 0=box_base, 1=box_lid

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
// Derived Dimensions (RESEARCH §5.1.2, §8.2)
// ---------------------------------------------------------------------------
_rib_w = rib_width;
_rib_tip_w = rib_profile == 0 ? _rib_w * 0.6 : _rib_w;
_slot_w = slot_width(_st, tolerance_z);
_pitch = pitch(_slot_w, _rib_w);

// Rib / slot height: slides sit in slots up to half their width
_slot_depth = _sw * 0.6;
_rib_height = _slot_depth;
_chamfer_h = rib_profile == 0 ? min(2.0, _rib_height * 0.15) : 0;

// Body envelope
_body_x = (num_slots * _pitch) + _rib_w + (2 * wall_thickness);
_body_y = _sl + (2 * wall_thickness) + tolerance_xy;
_body_z = _rib_height + floor_thickness;

// Lid dimensions
_lid_clearance = 0.3;
_lid_wall = 1.5;
_lid_z = 8;   // lid height

// Snap latch (RESEARCH §5.3)
_latch_arm_len = 15;    // PLA yield-safe minimum
_latch_arm_w = 6;
_latch_arm_t = 1.2;
_latch_hook_h = 2;
_latch_hook_d = 1.5;

// Stacking lip (RESEARCH §4.4)
_lip_h = 3;
_lip_w = 1.5;

// ---------------------------------------------------------------------------
// box_base — Slotted trough with ribs
// ---------------------------------------------------------------------------
module box_base() {
    difference() {
        union() {
            // Outer shell
            cube([_body_x, _body_y, _body_z]);

            // Stacking lip on top perimeter
            if (stackable == 1) {
                translate([0, 0, _body_z])
                    stacking_lip(_body_x, _body_y, _lip_h, _lip_w);
            }
        }

        // Hollow interior
        translate([wall_thickness, wall_thickness, floor_thickness])
            cube([
                _body_x - 2 * wall_thickness,
                _body_y - 2 * wall_thickness,
                _rib_height + 1  // cut above rib height
            ]);
    }

    // Rib array inside the box
    translate([wall_thickness, wall_thickness, floor_thickness]) {
        _tapered = rib_profile == 0 ? true : false;
        // Rotate ribs so they extrude along Y (slide length direction)
        rotate([0, 0, 0])
            slot_array(
                count = num_slots,
                pitch = _pitch,
                height = _rib_height,
                depth = _body_y - 2 * wall_thickness,
                root_w = _rib_w,
                tip_w = _rib_tip_w,
                chamfer_h = _chamfer_h,
                tapered = _tapered
            );
    }

    // Snap latch catches on base (one per long side)
    if (lid_latch == 0) {
        // Front catch
        translate([_body_x / 2 - _latch_arm_w / 2, -0.01, _body_z - _latch_hook_h - 1])
            snap_latch_catch(_latch_arm_w, _latch_hook_h, wall_thickness + _latch_hook_d);

        // Back catch
        translate([_body_x / 2 - _latch_arm_w / 2, _body_y - wall_thickness - _latch_hook_d + 0.01, _body_z - _latch_hook_h - 1])
            snap_latch_catch(_latch_arm_w, _latch_hook_h, wall_thickness + _latch_hook_d);
    }

    // Label recess on front face
    if (label_area == 1) {
        _label_w = min(40, _body_x * 0.5);
        _label_h = min(12, _body_z * 0.4);
        translate([(_body_x - _label_w) / 2, -0.01, (_body_z - _label_h) / 2])
            rotate([90, 0, 0])
                translate([0, 0, -0.4])
                    label_recess(_label_w, _label_h, 0.5);
    }

    // Debossed slot numbers (suppress when fn=0 for draft speed)
    if (numbering_start >= 0 && fn > 0) {
        for (i = [0 : num_slots - 1]) {
            _num = numbering_start + i;
            _x = wall_thickness + (i * _pitch) + _pitch / 2;
            translate([_x, _body_y - 0.01, floor_thickness + 2])
                rotate([90, 0, 0])
                    linear_extrude(height = 0.5)
                        text(str(_num), size = min(3, _pitch * 0.7),
                             halign = "center", valign = "bottom",
                             font = "Liberation Sans:style=Bold");
        }
    }
}

// ---------------------------------------------------------------------------
// box_lid — Snap-fit lid
// ---------------------------------------------------------------------------
module box_lid() {
    _inner_x = _body_x + _lid_clearance * 2;
    _inner_y = _body_y + _lid_clearance * 2;
    _outer_x = _inner_x + _lid_wall * 2;
    _outer_y = _inner_y + _lid_wall * 2;

    difference() {
        // Outer lid shell
        cube([_outer_x, _outer_y, _lid_z]);

        // Hollow interior (slides over base top)
        translate([_lid_wall, _lid_wall, 1.5])
            cube([_inner_x, _inner_y, _lid_z]);

        // Stacking groove on top (if stackable)
        if (stackable == 1) {
            translate([_lid_wall - _lip_w - 0.1,
                       _lid_wall - _lip_w - 0.1,
                       _lid_z - 3.2])
                stacking_groove(_inner_x + (_lip_w + 0.1) * 2,
                                _inner_y + (_lip_w + 0.1) * 2,
                                3.2, _lip_w + 0.2);
        }
    }

    // Snap latch arms (one per long side)
    if (lid_latch == 0) {
        // Front arm
        translate([_outer_x / 2 - _latch_arm_w / 2, 0, _lid_z])
            rotate([0, 0, 0])
                mirror([0, 0, 1])
                    snap_latch_arm(_latch_arm_len, _latch_arm_w,
                                   _latch_arm_t, _latch_hook_h, _latch_hook_d);

        // Back arm
        translate([_outer_x / 2 - _latch_arm_w / 2, _outer_y - _latch_arm_t, _lid_z])
            rotate([0, 0, 0])
                mirror([0, 0, 1])
                    snap_latch_arm(_latch_arm_len, _latch_arm_w,
                                   _latch_arm_t, _latch_hook_h, _latch_hook_d);
    }

    // Label recess on lid top
    if (label_area == 1) {
        _label_w = min(50, _outer_x * 0.6);
        _label_h = min(20, _outer_y * 0.3);
        translate([(_outer_x - _label_w) / 2, (_outer_y - _label_h) / 2, _lid_z - 0.39])
            label_recess(_label_w, _label_h, 0.4);
    }
}

// ---------------------------------------------------------------------------
// Render Mode Dispatch
// ---------------------------------------------------------------------------
if (render_mode == 0) {
    box_base();
}

if (render_mode == 1) {
    box_lid();
}
