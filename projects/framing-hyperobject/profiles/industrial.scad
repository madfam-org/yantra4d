include <BOSL2/std.scad>

// --- Textile / Canvas Profiles ---

// Stretcher Bar: Classic wooden profile with beaded edge
function stretcher_profile(depth = 19, width = 45) =
  [
    [0, 0],
    [width, 0], // Back
    [width, depth], // Outer edge
    [5, depth], // Front face
    [3, depth + 2], // Beaded lip (lifts canvas)
    [0, depth + 2], // Inner lip
    [0, 5], // Chamfer return
  ];

// SEG Extrusion: Aluminum channel for silicone edge graphics
function seg_profile(depth = 20, width = 20, channel_w = 3, channel_d = 12) =
  [
    [0, 0],
    [width, 0], // Back
    [width, depth], // Outer wall
    [width, depth], // Front (simplified)
    [width - 2, depth], // Lip
    [width - 2, depth - channel_d], // Channel down
    [width - 2 - channel_w, depth - channel_d], // Channel bottom
    [width - 2 - channel_w, depth], // Channel up
    [0, depth], // Inner wall
    [0, 0],
  ];

// --- Industrial Profiles ---

// Snap Frame: Base profile only (simplified mechanism geometry)
function snap_base_profile(width = 25, depth = 10) =
  [
    [0, 0],
    [width, 0],
    [width, 2], // Hinge mount area
    [width - 5, depth], // Inner slope
    [0, depth],
    [0, 0],
  ];

// --- Renderer ---

module render_textile_profile(path, type = "stretcher", w = 45, d = 19) {
  p =
    (type == "stretcher") ? stretcher_profile(d, w)
    : seg_profile(d, w);
  path_sweep(p, path, closed=true);
}

module render_industrial_profile(path, type = "snap", w = 25, d = 10) {
  p = snap_base_profile(w, d);
  path_sweep(p, path, closed=true);
}
