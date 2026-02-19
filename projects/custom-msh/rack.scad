// ============================================================================
// rack.scad — AOCL 10-Slot Substrate Rack (NATIVE)
// ============================================================================
// Copyright (c) 2026 madfam-org
// Licensed under the CERN Open Hardware Licence Version 2 - Weakly Reciprocal (CERN-OHL-W-2.0).

use <aocl_lib.scad>
include <BOSL2/std.scad>

// --- Configuration Parameters ---
// Standard slide dimensions
custom_slide_length = 25.4;
custom_slide_width = 25.4;
custom_slide_thickness = 1.0;

// Clearances and walls
tolerance_xy = 0.4;
tolerance_z = 0.2;
wall_thickness = 2.0;

// Features and capacities
num_slots = 10;
handle = 1;
open_bottom = 1;
drainage_angle = 5;
label_area = 1;
numbering_start = 1;
fn = 0;
$fn = fn > 0 ? fn : 32;

// --- Derived Geometry / Math ---

_min_rib_w = 2.0;
// Calculate precise slot aperture and overall pitch per slide
_slot_w = slot_width(custom_slide_thickness, tolerance_z);
_pitch = pitch(_slot_w, _min_rib_w);

_slot_depth = custom_slide_width + tolerance_xy;
_rib_height = _slot_depth;
_chamfer_h = min(1.5, _rib_height * 0.15);

// Structural elements sizing
_pillar_w = wall_thickness;
_crossbar_w = 3.0; // Base crossbar width if open_bottom is enabled
_crossbar_h = 2.5;

// Overall bounding box of the main lattice
_body_x = (num_slots * _pitch) + _min_rib_w + (2 * _pillar_w);
_body_y = custom_slide_length + (2 * _pillar_w) + tolerance_xy;
_base_h = open_bottom == 1 ? _crossbar_h : wall_thickness;
_body_z = _rib_height + _base_h;

// Handles and labels sizing
_handle_w = min(_body_x * 0.7, 70);
_handle_h = 14;
_handle_thick = 3.5;
_label_w = min(30, _body_x * 0.5);
_label_h = min(10, _body_z * 0.4);
_num_size = min(2.5, _pitch * 0.7);

// --- Core Modules ---

// Builds the structural lattice of the rack and populates the retention ribs
module rack_body() {
  // Construct upper structural rim frame
  translate([0, 0, _body_z - _crossbar_h]) cube([_body_x, _pillar_w, _crossbar_h]);
  translate([0, _body_y - _pillar_w, _body_z - _crossbar_h]) cube([_body_x, _pillar_w, _crossbar_h]);
  translate([0, 0, _body_z - _crossbar_h]) cube([_pillar_w, _body_y, _crossbar_h]);
  translate([_body_x - _pillar_w, 0, _body_z - _crossbar_h]) cube([_pillar_w, _body_y, _crossbar_h]);

  // Construct 4 corner pillars
  cube([_pillar_w, _pillar_w, _body_z]);
  translate([_body_x - _pillar_w, 0, 0]) cube([_pillar_w, _pillar_w, _body_z]);
  translate([0, _body_y - _pillar_w, 0]) cube([_pillar_w, _pillar_w, _body_z]);
  translate([_body_x - _pillar_w, _body_y - _pillar_w, 0]) cube([_pillar_w, _pillar_w, _body_z]);

  // Bottom plate (either skeletal frame or solid floor)
  if (open_bottom == 1) {
    // Skeletal crossbar base
    cube([_body_x, _pillar_w, _crossbar_h]);
    translate([0, _body_y - _pillar_w, 0]) cube([_body_x, _pillar_w, _crossbar_h]);
    cube([_pillar_w, _body_y, _crossbar_h]);
    translate([_body_x - _pillar_w, 0, 0]) cube([_pillar_w, _body_y, _crossbar_h]);
    for (frac = [0.33, 0.67])
      translate([0, _body_y * frac - _crossbar_w / 2, 0])
        cube([_body_x, _crossbar_w, _crossbar_h]);
  } else {
    // Solid base
    cube([_body_x, _body_y, wall_thickness]);
  }

  // Generate array of retention ribs along the front
  translate([_pillar_w, 0, _base_h]) {
    for (i = [0:num_slots]) {
      translate([i * _pitch, 0, 0])
        aocl_retention_rib(height=_rib_height, depth=_pillar_w, root_w=_min_rib_w, tip_w=_min_rib_w * 0.65, chamfer_h=_chamfer_h);
    }
  }

  // Generate array of retention ribs along the back
  translate([_pillar_w, _body_y - _pillar_w, _base_h]) {
    for (i = [0:num_slots]) {
      translate([i * _pitch, 0, 0])
        aocl_retention_rib(height=_rib_height, depth=_pillar_w, root_w=_min_rib_w, tip_w=_min_rib_w * 0.65, chamfer_h=_chamfer_h);
    }
  }

  // Draw the overhead carrying handle if enabled
  if (handle == 1) {
    _hx = (_body_x - _handle_w) / 2;
    _hy = (_body_y - _handle_thick) / 2;
    _hz = _body_z;
    translate([_hx, _hy, _hz]) cube([_handle_thick, _handle_thick, _handle_h]);
    translate([_hx + _handle_w - _handle_thick, _hy, _hz]) cube([_handle_thick, _handle_thick, _handle_h]);
    translate([_hx, _hy, _hz + _handle_h - _handle_thick]) cube([_handle_w, _handle_thick, _handle_thick]);
  }
}

// Extrudes slot numbers on the frame to identify sample locations
module slot_numbers() {
  if (fn > 0) {
    for (i = [0:num_slots - 1]) {
      _num = numbering_start + i;
      _rib_x = _pillar_w + (i * _pitch);

      // Position the number precisely above each slot opening
      translate([_rib_x + _num_size / 2 + 0.4, -0.01, _base_h + _rib_height * 0.4])
        rotate([90, 0, 0])
          linear_extrude(height=0.5)
            text(str(_num), size=_num_size, halign="center", valign="center", font="Liberation Sans:style=Bold");
    }
  }
}

// Subtracts geometry from the solid body to form a labeling recess
module rack_label() {
  if (label_area == 1) {
    translate([(_body_x - _label_w) / 2, -0.01, (_body_z - _label_h) / 2])
      rotate([90, 0, 0])
        translate([0, 0, -0.4])
          aocl_label_recess(_label_w, _label_h, 0.5);
  }
}

// Ensure the label recess is subtracted out of the framework, then append raised slot numbers
difference() {
  rack_body();
  rack_label();
}
slot_numbers();
