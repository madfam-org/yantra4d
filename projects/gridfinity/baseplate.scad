// Yantra4D Gridfinity Baseplate - BOSL2 Implementation
// Clean room native Rewrite
include <../../libs/BOSL2/std.scad>

width_units = 2;
depth_units = 2;
bp_enable_magnets = false;
bp_enable_screws = false;
bp_corner_radius = 3.75;
fn = 0;
$fa = 6; $fs = 0.1; $fn = fn > 0 ? fn : 32;

pitch = 42;
overall_z = 5;

module baseplate_profile() {
    rect([width_units*pitch, depth_units*pitch], rounding=bp_corner_radius);
}

module gridfinity_baseplate() {
    difference() {
        linear_extrude(overall_z) baseplate_profile();
        for (x=[0:width_units-1], y=[0:depth_units-1]) {
            translate([x*pitch - (width_units*pitch)/2 + pitch/2, y*pitch - (depth_units*pitch)/2 + pitch/2, overall_z]) {
                // Top cup indent (simplified BOSL2 prismoid)
                down(5) prismoid(size1=[39.2, 39.2], size2=[42, 42], h=5, rounding1=bp_corner_radius, rounding2=bp_corner_radius, anchor=BOT);
            }
        }
        if (bp_enable_screws) {
            for (x=[0:width_units-1], y=[0:depth_units-1]) {
                translate([x*pitch - (width_units*pitch)/2 + pitch/2, y*pitch - (depth_units*pitch)/2 + pitch/2, 0]) {
                    cylinder(d=3.2, h=10, anchor=BOT);
                }
            }
        }
    }
}
gridfinity_baseplate();
