include <../../libs/BOSL2/std.scad>

// AOCL Custom Holder
// 5" x 3" x 0.59" (127 x 76.2 x 15 mm)
// Center hole: 1" x 1" (25.4 x 25.4 mm)

$fn = 64;

width = 3 * 25.4; // 3 inches = 76.2mm
length = 5 * 25.4; // 5 inches = 127mm
thickness = 15; // 0.59 inches approx 15mm (14.986)

hole_size = 25.4; // 1 inch

diff("hole")
  cuboid([length, width, thickness], anchor=CENTER) {
    tag("hole")
      cuboid([hole_size, hole_size, thickness + 1], anchor=CENTER);
  }
