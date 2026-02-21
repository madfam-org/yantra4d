include <BOSL2/std.scad>
include <BOSL2/beziers.scad>

// --- Classic Profiles ---

// Ogee Profile: S-curve
function ogee_profile(w, d, rabbet_d = 10, rabbet_w = 5) =
  concat(
    [[0, 0]],
    bezier_curve(
      [
        [w / 3, 0], // Start of curve
        [w / 2, d / 4], // Control 1
        [w / 2, d * 0.75], // Control 2
        [w, d], // Top lip
      ], 20
    ),
    [
      [w, d - rabbet_d], // Rabbet depth drop
      [w - rabbet_w, d - rabbet_d], // Rabbet width return
      [w - rabbet_w, 0], // Inner wall
      [0, 0], // Close loop
    ]
  );

// Bevel Profile: Simple Chamfer
function bevel_profile(w, d, rabbet_d = 10, rabbet_w = 5) =
  [
    [0, 0],
    [w, d], // Slope up
    [w, d - rabbet_d], // Rabbet drop
    [w - rabbet_w, d - rabbet_d], // Rabbet return
    [w - rabbet_w, 0], // Inner wall
    [0, 0],
  ];

// Box Profile: Rectangular
function box_profile(w, d, rabbet_d = 10, rabbet_w = 5) =
  [
    [0, 0],
    [0, d], // Outer wall
    [w, d], // Top face
    [w, d - rabbet_d], // Rabbet drop
    [w - rabbet_w, d - rabbet_d], // Rabbet return
    [w - rabbet_w, 0], // Inner wall
    [0, 0],
  ];

module render_profile(path_width, path_height, profile_type = "ogee", w = 20, d = 15, rabbet_d = 10, rabbet_w = 5) {
  p =
    (profile_type == "ogee") ? ogee_profile(w, d, rabbet_d, rabbet_w)
    : (profile_type == "bevel") ? bevel_profile(w, d, rabbet_d, rabbet_w)
    : box_profile(w, d, rabbet_d, rabbet_w); // Default to box

  // Convert profile to 3D YZ plane, extrude, and cut miters
  module make_side(l) {
    difference() {
      // Extrude profile. The profile X is width, Y is height.
      // We orient it so profile X -> outward (Y), profile Y -> upward (Z).
      rotate([0, 0, -90])
        rotate([90, 0, 0])
          linear_extrude(l + w * 2 + 20, center=true)
            polygon(p);

      // Cut right miter (X > L/2 + Y => X - Y > L/2)
      // Cut left miter  (X < -L/2 - Y => X + Y < -L/2)
      // We can use a large box rotated at 45 degrees.
      translate([l / 2, 0, 0])
        rotate([0, 0, 45])
          translate([0, -500, -500])
            cube([1000, 1000, 1000]);

      translate([-l / 2, 0, 0])
        rotate([0, 0, 135])
          translate([0, -500, -500])
            cube([1000, 1000, 1000]);
    }
  }

  union() {
    translate([0, path_height / 2, 0]) make_side(path_width);
    translate([0, -path_height / 2, 0]) rotate([0, 0, 180]) make_side(path_width);
    translate([path_width / 2, 0, 0]) rotate([0, 0, -90]) make_side(path_height);
    translate([-path_width / 2, 0, 0]) rotate([0, 0, 90]) make_side(path_height);
  }
}
