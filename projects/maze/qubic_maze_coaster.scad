// Qubic wrapper — Maze Coaster
// Flat circular coaster with maze walls on top

rows = 10;
cols = 10;
cell_size = 5;
wall_thickness = 1.2;
wall_height = 3;
base_thickness = 2;
seed = 123;
diameter = 100;
render_mode = 0;

use <maze/mz_square.scad>
use <maze/mz_squarewalls.scad>
use <line2d.scad>

radius = diameter / 2;

// Generate maze
cells = mz_square(rows, cols, seed = seed);
walls = mz_squarewalls(cells, cell_size);

// Center the maze on origin
maze_w = cols * cell_size;
maze_h = rows * cell_size;

union() {
    // Base disc
    cylinder(h = base_thickness, r = radius);

    // Maze walls clipped to circle
    translate([0, 0, base_thickness])
        intersection() {
            cylinder(h = wall_height, r = radius - 1);
            translate([-maze_w / 2, -maze_h / 2, 0])
                linear_extrude(wall_height)
                    for (wall = walls)
                        line2d(wall[0], wall[1], width = wall_thickness);
        }
}
