// =============================================================================
// Yantra4D Core CDG (Common Denominator Geometry) Interfaces
// Provides common standardized connections (threads, cleats, standoffs, snaps)
// =============================================================================

include <../scad_core/core.scad>

// --- VESA Standards ---
function vesa_spec(standard) =
  (standard == "MIS-D 75") ? [75, 75, 4]
  : (standard == "MIS-D 100") ? [100, 100, 4]
  : (standard == "MIS-E") ? [200, 100, 4]
  : [100, 100, 4]; // Default

module y4d_vesa_pattern(standard = "MIS-D 100", center = true) {
  spec = vesa_spec(standard);
  sx = spec[0];
  sy = spec[1];
  d = spec[2];

  translate(center ? [-sx / 2, -sy / 2, 0] : [0, 0, 0]) {
    circle(d=d);
    translate([sx, 0, 0]) circle(d=d);
    translate([0, sy, 0]) circle(d=d);
    translate([sx, sy, 0]) circle(d=d);
  }
}

// --- French Cleat ---
module y4d_french_cleat(length = 100, height = 30, depth = 15, angle = 45) {
  polygon_points = [
    [0, 0],
    [depth, 0],
    [depth, height],
    [depth - (height * tan(angle)), height],
  ];
  translate([-length / 2, -height / 2, 0])
    rotate([90, 0, 90])
      linear_extrude(height=length) {
        polygon(points=polygon_points);
      }
}

// --- Standoffs ---
module y4d_standoff_barrel(h = 20, d = 12, thread_d = 4) {
  difference() {
    cylinder(h=h, d=d);
    translate([0, 0, -1]) cylinder(h=h + 2, d=thread_d);
  }
}

module y4d_standoff_set(spacing_x = 100, spacing_y = 100, h = 25) {
  sx = spacing_x / 2;
  sy = spacing_y / 2;
  translate([-sx, -sy, 0]) y4d_standoff_barrel(h=h);
  translate([sx, -sy, 0]) y4d_standoff_barrel(h=h);
  translate([-sx, sy, 0]) y4d_standoff_barrel(h=h);
  translate([sx, sy, 0]) y4d_standoff_barrel(h=h);
}

// --- Snap Latch ---
module y4d_snap_latch_arm(arm_length, arm_width, arm_thick, hook_height, hook_depth) {
  union() {
    cube([arm_thick, arm_width, arm_length]);
    translate([arm_thick, 0, arm_length - hook_height])
      cube([hook_depth, arm_width, hook_height]);
  }
}

module y4d_snap_latch_catch(width, height, depth) {
  difference() {
    cube([depth, width, height]);
    translate([1, -1, 1])
      cube([depth - 1, width + 2, height - 2]);
  }
}
