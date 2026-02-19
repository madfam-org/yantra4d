// ============================================================================
// stemfie_core.scad — Native BOSL2 Stemfie Core
// ============================================================================
// Copyright (c) 2026 madfam-org
// Licensed under the CERN Open Hardware Licence Version 2 - Weakly Reciprocal (CERN-OHL-W-2.0).

include <../../libs/BOSL2/std.scad>

BU = 10; // Block Unit (10mm standard stemfie)
HOLE_D = 4.2; // Standard clearance hole for pins/screws
SLOT_D = HOLE_D;
CHAMFER = 0.5;

length_units = is_undef(length_units) ? 4 : length_units;
width_units = is_undef(width_units) ? 1 : width_units;
height_units = is_undef(height_units) ? 1 : height_units;
holes_x = is_undef(holes_x) ? true : holes_x;
holes_y = is_undef(holes_y) ? true : holes_y;
holes_z = is_undef(holes_z) ? true : holes_z;

arm_a_units = is_undef(arm_a_units) ? 3 : arm_a_units;
arm_b_units = is_undef(arm_b_units) ? 3 : arm_b_units;
thickness_units = is_undef(thickness_units) ? 1 : thickness_units;
holes_enabled = is_undef(holes_enabled) ? true : holes_enabled;

fastener_type_id = is_undef(fastener_type_id) ? 0 : fastener_type_id;

$fn = is_undef(fn) || fn == 0 ? 32 : fn;

module stemfie_hole_pattern(l, w, h, hx, hy, hz) {
  if (hz) {
    for (i = [0:l - 1])
      for (j = [0:w - 1]) {
        translate([-l * BU / 2 + i * BU + BU / 2, -w * BU / 2 + j * BU + BU / 2, 0])
          cylinder(d=HOLE_D, h=h * BU + 1, center=true);
      }
  }
  if (hx) {
    for (j = [0:w - 1])
      for (k = [0:h - 1]) {
        translate([0, -w * BU / 2 + j * BU + BU / 2, -h * BU / 2 + k * BU + BU / 2])
          yrot(90) cylinder(d=HOLE_D, h=l * BU + 1, center=true);
      }
  }
  if (hy) {
    for (i = [0:l - 1])
      for (k = [0:h - 1]) {
        translate([-l * BU / 2 + i * BU + BU / 2, 0, -h * BU / 2 + k * BU + BU / 2])
          xrot(90) cylinder(d=HOLE_D, h=w * BU + 1, center=true);
      }
  }
}

module stemfie_beam() {
  difference() {
    cuboid([length_units * BU, width_units * BU, height_units * BU], chamfer=CHAMFER, anchor=CENTER);
    stemfie_hole_pattern(length_units, width_units, height_units, holes_x, holes_y, holes_z);
  }
}

module stemfie_brace() {
  // A 90-degree corner brace (L-shape)
  _th = thickness_units * (BU / 4); // thickness multiplier
  difference() {
    union() {
      translate([arm_a_units * BU / 2 - BU / 2, 0, 0])
        cuboid([arm_a_units * BU, BU, _th], chamfer=CHAMFER, anchor=CENTER);
      translate([0, arm_b_units * BU / 2 - BU / 2, 0])
        cuboid([BU, arm_b_units * BU, _th], chamfer=CHAMFER, anchor=CENTER);
    }
    if (holes_enabled) {
      for (i = [0:arm_a_units - 1]) {
        translate([i * BU, 0, 0])
          cylinder(d=HOLE_D, h=_th + 1, center=true);
      }
      for (j = [1:arm_b_units - 1]) {
        translate([0, j * BU, 0])
          cylinder(d=HOLE_D, h=_th + 1, center=true);
      }
    }
  }
}

module stemfie_fastener() {
  _h = length_units * BU;
  if (fastener_type_id == 0) {
    // Pin (solid cylinder with chamfered ends and a center stop)
    union() {
      cylinder(d=HOLE_D - 0.2, h=_h, center=true, chamfer=0.5);
      cylinder(d=HOLE_D + 1.5, h=2, center=true, chamfer=0.5);
    }
  } else {
    // Shaft (just a solid continuous rod)
    cylinder(d=HOLE_D - 0.2, h=_h, center=true, chamfer=0.5);
  }
}

// Dispatch based on render_part injected by wrapper
if (render_part == "beam") {
  stemfie_beam();
} else if (render_part == "brace") {
  stemfie_brace();
} else if (render_part == "fastener") {
  stemfie_fastener();
}
