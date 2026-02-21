// Yantra4D Torus Knot Sculpture
// Uses dotSCAD torus_knot path + BOSL2 sweep for solid geometry
//
// A torus knot is defined by integers (p, q) that describe how the
// curve winds around the torus surface.

use <dotSCAD/src/torus_knot.scad>
include <../../libs/BOSL2/std.scad>
include <../../libs/BOSL2/skin.scad>

// --- Parameters (overridden by platform) ---
p = 2;
q = 3;
tube_radius = 4;
torus_radius = 30;
segments = 120;
scale_factor = 1.0;
fn = 0;
render_mode = 0;

$fn = fn > 0 ? fn : 24;

// Generate the torus knot path using dotSCAD
knot_path = torus_knot(p, q, phi_step = 360 / segments);

// Scale the path to desired torus radius
scaled_path = [for (pt = knot_path) pt * torus_radius / 10 * scale_factor];

// Create circular cross-section profile
function circle_profile(r, n=16) =
    [for (i = [0:n-1]) [r * cos(i * 360/n), r * sin(i * 360/n)]];

// Sweep a circular profile along the knot path
module knot_body() {
    path_sweep(circle_profile(tube_radius, $fn), scaled_path, closed=true);
}

// --- Render ---
if (render_mode == 0) {
    knot_body();
}
