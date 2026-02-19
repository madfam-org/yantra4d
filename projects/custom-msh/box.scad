// ============================================================================
// box.scad — AOCL Outer Box (Portamuestras) (NATIVE)
// ============================================================================
// Copyright (c) 2026 madfam-org
// Licensed under the CERN Open Hardware Licence Version 2 - Weakly Reciprocal (CERN-OHL-W-2.0).

use <aocl_lib.scad>
include <BOSL2/std.scad>

// --- Configuration Parameters ---

// Accommodated slide dimensions
custom_slide_length = 25.4;
custom_slide_width = 25.4;
custom_slide_thickness = 1.0;

// Fits and Tolerances
tolerance_xy = 0.4;
tolerance_z = 0.2;
wall_thickness = 2.0;

// Global Setup
num_racks = 3;
box_depth_target = 26.0;
snap_lid = 1;
label_area = 1;
fn = 0;

// Part renderer (0 = Base, 1 = Lid)
render_mode = 0;

$fn = fn > 0 ? fn : 32;

// --- Imposed Rack Math ---
// Recalculating the physical rack dimensions so the box fits perfectly around them
_min_rib_w = 2.0;
_slot_w = slot_width(custom_slide_thickness, tolerance_z);
_pitch = pitch(_slot_w, _min_rib_w);
_num_slots = 10;
_pillar_w = wall_thickness;

_rack_x = (_num_slots * _pitch) + _min_rib_w + (2 * _pillar_w);
_rack_y = custom_slide_length + (2 * _pillar_w) + tolerance_xy;
_slot_depth = custom_slide_width + tolerance_xy;
_crossbar_h = 2.5;

_rack_z = _slot_depth + _crossbar_h;
_handle_h = 14;
_total_rack_h = _rack_z + _handle_h;

// --- Box Calculations ---

_rack_clearance = 0.5;

// Inner cavity to hold all racks plus clearance margins across dimensions
_inner_x = num_racks * (_rack_x + _rack_clearance) + _rack_clearance;
_inner_y = _rack_y + _rack_clearance * 2;
_inner_z = max(box_depth_target - 2 * wall_thickness, _rack_z + _rack_clearance);

// Outer shell size
_box_x = _inner_x + 2 * wall_thickness;
_box_y = _inner_y + 2 * wall_thickness;
_box_z = _inner_z + wall_thickness;

// Inner dividing rails
_guide_h = _crossbar_h + 2;
_guide_w = 1.5;
_guide_d = _inner_y;

// Latch arm specifications
_latch_arm_len = 15;
_latch_arm_w = 8;
_latch_arm_t = 1.2;
_latch_hook_h = 2;
_latch_hook_d = 1.5;

// Lid specs
_lid_clearance = 0.3;
_lid_wall = 1.5;
// Target lid depth to clear rack handles
_lid_z = max(12, _handle_h + 2);

_label_w = min(60, _box_x * 0.55);
_label_h = min(18, _box_y * 0.35);

// --- Core Modules ---

// Build internal ribs preventing the racks from shifting laterally
module rack_guide_rails() {
  for (r = [0:num_racks - 1]) {
    _rx = wall_thickness + _rack_clearance + r * (_rack_x + _rack_clearance);

    // Left guide for current rack index
    translate([_rx - _guide_w, wall_thickness, wall_thickness])
      cube([_guide_w, _guide_d, _guide_h]);

    // Right guide for current rack index
    translate([_rx + _rack_x, wall_thickness, wall_thickness])
      cube([_guide_w, _guide_d, _guide_h]);
  }
}

// Bottom enclosure shell
module box_base() {
  difference() {
    union() {
      // Main outer box shell
      cuboid([_box_x, _box_y, _box_z], rounding=1.5, edges=[BOTTOM], anchor=BOTTOM + LEFT + FRONT);

      // Build catching mechanisms on front and back if snap_lid is enabled
      if (snap_lid == 1) {
        translate([_box_x / 2 - _latch_arm_w / 2, -0.01, _box_z - _latch_hook_h - 1])
          aocl_snap_catch(_latch_arm_w, _latch_hook_h, wall_thickness + _latch_hook_d);

        translate([_box_x / 2 - _latch_arm_w / 2, _box_y - wall_thickness - _latch_hook_d + 0.01, _box_z - _latch_hook_h - 1])
          aocl_snap_catch(_latch_arm_w, _latch_hook_h, wall_thickness + _latch_hook_d);
      }

      // Interior sorting rails
      rack_guide_rails();
    }

    // Core subtracted volume for the internal cavity
    translate([wall_thickness, wall_thickness, wall_thickness])
      cube([_inner_x, _inner_y, _inner_z + 1]);
  }

  // Deduct label volume from the front shell
  if (label_area == 1) {
    _lbl_w = min(40, _box_x * 0.45);
    _lbl_h = min(10, _box_z * 0.35);
    translate([(_box_x - _lbl_w) / 2, -0.01, (_box_z - _lbl_h) / 2])
      rotate([90, 0, 0])
        translate([0, 0, -0.4])
          aocl_label_recess(_lbl_w, _lbl_h, 0.5);
  }
}

// Top cap enclosure that fits over the base
module box_lid() {
  // Define lid outer boundaries expanding outside the main box 
  _o_x = _box_x + _lid_clearance * 2 + _lid_wall * 2;
  _o_y = _box_y + _lid_clearance * 2 + _lid_wall * 2;

  // Define lid inner cavity enclosing the base perimeter
  _i_x = _box_x + _lid_clearance * 2;
  _i_y = _box_y + _lid_clearance * 2;

  difference() {
    // Outer lid shell
    cuboid([_o_x, _o_y, _lid_z], rounding=1.5, edges=[TOP], anchor=BOTTOM + LEFT + FRONT);

    // Extrude out the inner cavity
    translate([_lid_wall, _lid_wall, 1.5]) cube([_i_x, _i_y, _lid_z]);

    // Mark label space on the ceiling of the lid
    if (label_area == 1) {
      translate([(_o_x - _label_w) / 2, (_o_y - _label_h) / 2, _lid_z - 0.39])
        aocl_label_recess(_label_w, _label_h, 0.4);
    }
  }

  // Draw two cantilever hooks locking into the base catches
  if (snap_lid == 1) {
    translate([_o_x / 2 - _latch_arm_w / 2, 0, _lid_z])
      mirror([0, 0, 1])
        aocl_snap_arm(_latch_arm_len, _latch_arm_w, _latch_arm_t, _latch_hook_h, _latch_hook_d);

    translate([_o_x / 2 - _latch_arm_w / 2, _o_y - _latch_arm_t, _lid_z])
      mirror([0, 0, 1])
        aocl_snap_arm(_latch_arm_len, _latch_arm_w, _latch_arm_t, _latch_hook_h, _latch_hook_d);
  }
}

// Render the selected discrete part
if (render_mode == 0) box_base();
if (render_mode == 1) {
  // Invert orientation relative to the box for an exploded presentation
  translate([0, 0, _box_z]) box_lid();
}
