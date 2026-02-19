// ============================================================================
// keycap.scad — Native BOSL2 Keycap Generator
// ============================================================================
// Copyright (c) 2026 madfam-org
// Licensed under the CERN Open Hardware Licence Version 2 - Weakly Reciprocal (CERN-OHL-W-2.0).
//
// Native recreation of mechanical keycap topology using BOSL2.

include <../../libs/BOSL2/std.scad>

// --- Parameters ---
profile_id = 0; // 0=DCS, 1=DSA, 2=SA, 3=OEM, 4=Cherry
row_id = 1;
key_size_id = 0; // 0=1u, 1=1.25u, 2=1.5u, 3=2u
stem_type_id = 0; // 0=Cherry MX, 1=Alps, 2=Box Cherry
legend_enabled = false;
legend_text = "A";
font_size = 6;
dish_depth = 1;
wall_thickness = 1.5; // per wall
keytop_thickness = 1;
stem_slop = 0.35;
fn = 0;

$fn = fn > 0 ? fn : 32;

// --- Profile Definitions ---
// Format: [height, top_tilt_angle, top_width, top_depth]
_profiles = [
  [9.5, -5, 12.0, 14.0], // DCS (approx)
  [8.0, 0, 12.5, 12.5], // DSA
  [16.0, 5, 12.7, 12.7], // SA
  [11.9, -5, 12.0, 14.0], // OEM
  [9.4, -5, 11.5, 13.5], // Cherry
];

_sizes = [1, 1.25, 1.5, 2];
_u = 19.05; // 1u standard size
_gap = 0.5; // clearance between caps

_w = _sizes[key_size_id] * _u - _gap * 2;
_d = _u - _gap * 2;
_prof = _profiles[profile_id];
_h = _prof[0] + (row_id - 2) * 0.5; // Pseudo row scaling
_tilt = _prof[1] + (row_id - 2) * 2;
_top_w = _prof[2] * _sizes[key_size_id]; // Scale top width based on size
_top_d = _prof[3];

// Convert tilt angle to shift magnitude
_shift_y = _h * tan(_tilt);

module keycap_shell() {
  difference() {
    // Outer Shell
    prismoid(
      size1=[_w, _d],
      size2=[_top_w, _top_d],
      h=_h,
      shift=[0, _shift_y],
      rounding=1.5,
      anchor=BOTTOM
    );

    // Inner Shell Void
    down(0.01)
      prismoid(
        size1=[_w - wall_thickness * 2, _d - wall_thickness * 2],
        size2=[_top_w - wall_thickness * 2, _top_d - wall_thickness * 2],
        h=_h - keytop_thickness,
        shift=[0, (_h - keytop_thickness) * tan(_tilt)],
        rounding=1.0,
        anchor=BOTTOM
      );

    // Spherical Dish Cutout on Top
    translate([0, _shift_y, _h + 20 - dish_depth])
      sphere(r=20, $fn=$fn * 2);

    // Legend engraving
    if (legend_enabled) {
      translate([-_top_w / 2 + 2, _shift_y + _top_d / 2 - 2, _h - dish_depth])
        linear_extrude(2)
          text(legend_text, size=font_size, font="Liberation Sans:style=Bold", valign="top", halign="left");
    }
  }
}

module stem_cherry() {
  _stem_d = 5.5;
  _cross_w = 1.17 + stem_slop / 2;
  _cross_l = 4.1 + stem_slop / 2;
  difference() {
    cylinder(d=_stem_d, h=_h - keytop_thickness - 0.5, anchor=BOTTOM);
    up(0.1) {
      cuboid([_cross_w, _cross_l, _h], anchor=BOTTOM);
      cuboid([_cross_l, _cross_w, _h], anchor=BOTTOM);
    }
  }
}

module stem_alps() {
  _stem_w = 4.5;
  _stem_d = 2.2;
  _hollow_w = 3.2 - stem_slop;
  _hollow_d = 1.2 - stem_slop;
  difference() {
    cuboid([_stem_w, _stem_d + 1, _h - keytop_thickness - 0.5], anchor=BOTTOM);
    up(0.1) cuboid([_hollow_w, _hollow_d, _h], anchor=BOTTOM);
  }
}

module stem_box_cherry() {
  // Cherry MX outer box bounds
  _box_out = 6.0;
  _cross_w = 1.17 + stem_slop / 2;
  _cross_l = 4.1 + stem_slop / 2;
  difference() {
    cuboid([_box_out, _box_out, _h - keytop_thickness - 0.5], anchor=BOTTOM);
    up(0.1) {
      cuboid([_cross_w, _cross_l, _h], anchor=BOTTOM);
      cuboid([_cross_l, _cross_w, _h], anchor=BOTTOM);
      // Hollow out inner corners
      cuboid([_box_out - 1.5, _box_out - 1.5, _h], anchor=BOTTOM);
    }
  }
}

module keycap_assembly() {
  keycap_shell();

  if (stem_type_id == 0) {
    stem_cherry();
  } else if (stem_type_id == 1) {
    stem_alps();
  } else {
    stem_box_cherry();
  }
}

keycap_assembly();
