// Yantra4D Gridfinity Lid - BOSL2 Implementation
include <../../libs/BOSL2/std.scad>

width_units = 2;
depth_units = 1;
fn = 0;
$fa = 6; $fs = 0.4; $fn = fn > 0 ? fn : 32;

pitch = 42;
corner_radius = 3.75;

module gridfinity_lid() {
    total_w = width_units * pitch - 1;
    total_d = depth_units * pitch - 1;
    total_h = 2;
    
    // Core geometry
    cuboid([total_w, total_d, total_h], p1=[-total_w/2, -total_d/2, 0], rounding=corner_radius, edges="Z");
}

gridfinity_lid();
