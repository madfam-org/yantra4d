// --- VESA Standards ---

// Returns [spacing_x, spacing_y, screw_dia]
function vesa_spec(standard) =
  (standard == "MIS-D 75") ? [75, 75, 4]
  : (standard == "MIS-D 100") ? [100, 100, 4]
  : (standard == "MIS-E") ? [200, 100, 4]
  : [100, 100, 4]; // Default

module vesa_pattern(standard = "MIS-D 100", center = true) {
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

module french_cleat(length = 100, depth = 10, angle = 45) {
  // 45 degree simple cleat profile
  polygon(
    [
      [0, 0],
      [length, 0],
      [length, depth],
      [0, depth - (depth * tan(90 - angle))],
    ]
  );
}
