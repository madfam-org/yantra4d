// Qubic wrapper — Voronoi Vase
// Cylindrical vase with voronoi pattern walls

cell_count = 20;
size = 100;          // diameter in mm
thickness = 3;
cell_wall = 2;
seed = 42;
height = 120;
fn = 0;
render_mode = 0;

$fn = fn > 0 ? fn : 32;

use <voronoi/vrn2_space.scad>

radius = size / 2;
circumference = PI * size;
grid_w = circumference / ceil(sqrt(cell_count));

// Solid cylinder shell minus voronoi cutouts
difference() {
    // Outer shell
    difference() {
        cylinder(h = height, r = radius, center = false);
        translate([0, 0, thickness])
            cylinder(h = height, r = radius - thickness, center = false);
    }

    // Voronoi cutouts through the wall
    // Project 2D voronoi onto cylinder surface by cutting from outside
    for (angle = [0:10:350]) {
        rotate([0, 0, angle])
            translate([radius, 0, 0])
                rotate([0, 90, 0])
                    linear_extrude(thickness * 3, center = true)
                        intersection() {
                            square([height - thickness * 2, size], center = true);
                            translate([-height/2, -size/2])
                                vrn2_space(
                                    size = [height, size],
                                    grid_w = grid_w,
                                    seed = seed,
                                    spacing = cell_wall
                                );
                        }
    }
}
