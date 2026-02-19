// Yantra4D wrapper — Voronoi Coaster
// Flat circular coaster with voronoi pattern cutouts

cell_count = 20;
size = 100;          // diameter in mm
thickness = 3;
cell_wall = 2;
seed = 42;
fn = 0;
render_mode = 0;

$fn = fn > 0 ? fn : 32;

use <voronoi/vrn2_space.scad>

radius = size / 2;
grid_w = size / ceil(sqrt(cell_count));

// Solid base disc minus voronoi cells
difference() {
    // Base disc
    cylinder(h = thickness, r = radius, center = false);

    // Voronoi cell cutouts — cut through the disc
    translate([0, 0, -0.5])
        linear_extrude(thickness + 1)
            intersection() {
                circle(r = radius - cell_wall);
                translate([-size/2, -size/2])
                    vrn2_space(size = [size, size], grid_w = grid_w,
                               seed = seed, spacing = cell_wall);
            }
}
