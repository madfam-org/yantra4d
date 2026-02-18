include <BOSL2/std.scad>
include <BOSL2/beziers.scad>

// --- Classic Profiles ---

// Ogee Profile: S-curve
function ogee_profile(w, d, rabbet_d = 10, rabbet_w = 5) =
  bez_path(
    [
      [0, 0],
      [w / 3, 0], // Bottom flat
      [w / 2, d / 4],
      [w / 2, d * 0.75], // S-curve inflection
      [w, d], // Top lip
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

// --- Renderer ---

module render_profile(path, profile_type = "ogee", w = 20, d = 15, rabbet_d = 10, rabbet_w = 5) {
  p =
    (profile_type == "ogee") ? ogee_profile(w, d, rabbet_d, rabbet_w)
    : (profile_type == "bevel") ? bevel_profile(w, d, rabbet_d, rabbet_w)
    : box_profile(w, d, rabbet_d, rabbet_w); // Default to box

  path_sweep(p, path, closed=true);
}
