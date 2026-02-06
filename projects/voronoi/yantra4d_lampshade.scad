// Yantra4D wrapper — Voronoi Lampshade
// Spherical lampshade with voronoi cell openings

cell_count = 20;
size = 100;          // diameter in mm
thickness = 3;
cell_wall = 2;
seed = 42;
height = 120;
fn = 0;
render_mode = 0;

$fn = fn > 0 ? fn : 32;

use <voronoi/vrn_sphere.scad>
use <fibonacci_lattice.scad>
use <polyline_join.scad>

radius = size / 2;

// Generate points on sphere using fibonacci lattice
pts = fibonacci_lattice(cell_count, radius);

// Compute voronoi cells on sphere
cells = vrn_sphere(pts);

// Hollow sphere shell with voronoi cell openings
difference() {
    // Outer sphere
    sphere(r = radius);

    // Inner sphere (hollow)
    sphere(r = radius - thickness);

    // Cut bottom opening for lamp fitting
    translate([0, 0, -radius])
        cylinder(h = radius * 0.4, r = radius * 0.3);

    // Voronoi cell openings — shrink each cell polygon and cut through
    for (cell = cells) {
        // Use polyline_join to create the cell outline, then cut
        hull()
            for (p = cell)
                translate(p * (1 + 0.01))
                    sphere(r = cell_wall / 2);
    }
}
